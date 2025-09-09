import logging
import time
import numpy as np

from numba import njit
from typing import Any, Dict, Set, Union
from aredis_om.model.model import NotFoundError
from fifi import RedisSubscriber, log_exception
from multiprocessing import Queue
from ..base import BaseIndicator
from ....enums.exchange import Exchange
from ....enums.market import Market
from ....enums.data_type import DataType
from ....models.rsi_model import RSIModel
from ....helpers.hyperliquid_helpers import *
from ...info.hyperliquid_info import HyperliquidInfo


LOGGER = logging.getLogger(__name__)


class HyperLiquidRSIIndicator(BaseIndicator):
    """
    RSI indicator engine for Hyperliquid exchange supporting multiple timeframes
    and periods. Runs in its own process with a multiprocessing queue for dynamic
    subscriptions.

    Attributes:
        indicator_name (str): Name of the indicator ('rsi').
        data_length (int): Maximum length of the close price buffer per timeframe.
        monitor_channel (str): Redis channel for receiving candle data.
        close_prices (Dict[str, np.ndarray]): Price buffers keyed by timeframe.
        subscribed_periods (Dict[str, Set[int]]): Periods being tracked per timeframe.
        monitor (RedisSubscriber): Redis subscriber for market data.
        rsi_model (RSIModel): Redis model to store RSI values.
        ready (bool): Indicates if the engine has received first candle and is ready.
        command_queue (Queue): Multiprocessing queue for dynamic subscription commands.
        current_candle (Dict[str, float]): Last processed candle timestamp per timeframe.
    """

    indicator_name: str = "rsi"
    data_length: int = 200  # Maximum buffer length for smoothing

    def __init__(self, exchange: Exchange, market: Market):
        """
        Initialize the RSI indicator engine.

        Args:
            exchange (Exchange): Exchange enum for which this indicator runs.
            market (Market): Market enum for which this indicator runs.
        """
        super().__init__(exchange=exchange, market=market, run_in_process=True)
        self.monitor_channel = f"{self.exchange.value}_{self.market.value}"

        # Buffers keyed only by timeframe
        self.close_prices: Dict[str, np.ndarray] = {}
        self.high_prices: Dict[str, np.ndarray] = {}  # per timeframe high buffer
        self.low_prices: Dict[str, np.ndarray] = {}  # per timeframe low buffer

        # Track subscribed periods per timeframe
        self.subscribed_periods: Dict[str, Set[int]] = {}

        # Redis subscriber + RSI model
        self.monitor: RedisSubscriber = None
        self.rsi_model: RSIModel = None

        # Engine state
        self.ready: bool = False

        # Queue for dynamic subscription commands (used across processes)
        self.command_queue = Queue()

        # Last processed candle per timeframe
        self.current_candle: Dict[str, float] = {}

    async def prepare(self) -> None:
        """
        Prepare the RSI engine before execution. This method initializes:

        1. The Redis subscriber for receiving candle updates.
        2. The Hyperliquid info client for fetching historical candle data.
        3. The RSIModel in Redis as a placeholder for storing computed RSI values.

        Notes:
            - The RSIModel is created with a dummy timeframe and period initially.
            Actual periods and timeframes are stored dynamically as subscriptions arrive.
            - This method should be called once at engine startup before `execute()`.
        """
        # Initialize Redis subscriber for monitoring candle data
        self.monitor = await RedisSubscriber.create(channel=self.monitor_channel)

        # Initialize Hyperliquid info client for fetching historical data
        self.info = HyperliquidInfo()

        # Initialize placeholder RSIModel in Redis
        # Dynamic periods/timeframes will be added during subscriptions
        self.rsi_model = await RSIModel.create(
            pk=self.pk,  # primary key for this indicator instance
            exchange=self.exchange,
            market=self.market,
            timeframe="",  # placeholder, actual timeframe assigned per subscription
            period=0,  # placeholder, actual period assigned per subscription
            rsi=0,  # initial RSI value
            time=time.time(),  # timestamp of creation
        )
        await self.rsi_model.save()

    @log_exception()
    async def execute(self) -> None:
        """
        Main loop for processing RSI subscriptions and market data in real-time.

        Responsibilities:
            1. Handles dynamic subscription commands via a multiprocessing queue.
            2. Maintains per-timeframe close price buffers.
            3. Computes RSI for all subscribed periods:
                - In-progress candle RSI updated on every tick.
                - Confirmed candle RSI shifted at candle close.
            4. Stores RSI values in Redis per (timeframe, period).
            5. Marks the engine as ready after processing the first candle.

        Notes:
            - Tick-level RSI updates allow detectors to react ASAP.
            - Buffer is only shifted when the candle closes.
            - Pre-fills buffers with historical closes for stable initial RSI.
        """

        while True:
            # -------------------------------
            # 1️⃣ Handle new subscription commands
            # -------------------------------
            while not self.command_queue.empty():
                cmd = self.command_queue.get()
                if cmd["action"] != "subscribe":
                    continue

                timeframe = cmd["timeframe"]
                period = cmd["period"]

                if timeframe not in self.close_prices:
                    await self.bootstrap_buffer(timeframe)
                    self.subscribed_periods[timeframe] = set()

                self.subscribed_periods[timeframe].add(period)
                LOGGER.info(f"{self.name}: subscribed to {timeframe}, period {period}")

            # -------------------------------
            # 2️⃣ Process incoming messages
            # -------------------------------
            msgs = await self.monitor.get_messages()
            for msg in msgs:
                if not msg or "i" not in msg["data"]:
                    continue

                timeframe = msg["data"]["i"]
                close = float(msg["data"]["c"])
                high = float(msg["data"]["h"])
                low = float(msg["data"]["l"])
                timestamp = float(msg["data"]["t"])

                if timeframe not in self.close_prices:
                    continue  # Should be handled by bootstrap

                # --- Assign buffers before use ---
                buffer_c = self.close_prices[timeframe]
                buffer_h = self.high_prices[timeframe]
                buffer_l = self.low_prices[timeframe]

                candle_closed = (
                    self.current_candle.get(timeframe) != timestamp
                    and self.current_candle.get(timeframe) is not None
                )

                if candle_closed:
                    # Shift buffers
                    buffer_c = np.roll(buffer_c, -1)
                    buffer_h = np.roll(buffer_h, -1)
                    buffer_l = np.roll(buffer_l, -1)

                    # Insert new candle
                    buffer_c[-1] = close
                    buffer_h[-1] = high
                    buffer_l[-1] = low
                    self.current_candle[timeframe] = timestamp
                else:
                    # Update in-progress candle
                    buffer_c[-1] = close
                    buffer_h[-1] = high
                    buffer_l[-1] = low

                # --- Compute RSI & ATR for all subscribed periods ---
                for period in self.subscribed_periods.get(timeframe, []):
                    rsi_val = round(_rsi_numba(buffer_c, period), 2)
                    atr_val = _atr_numba(buffer_h, buffer_l, buffer_c, period)

                    # Save/update model in Redis
                    pk = f"{self.exchange.value}_{self.market.value}_{timeframe}_{period}"
                    try:
                        rsi_model = await RSIModel.get_by_id(pk)
                    except NotFoundError:
                        rsi_model = await RSIModel.create(
                            pk=pk,
                            exchange=self.exchange,
                            market=self.market,
                            timeframe=timeframe,
                            period=period,
                            rsi=rsi_val,
                            atr=atr_val,
                            time=time.time(),
                        )
                        await rsi_model.save()
                    else:
                        await rsi_model.update(
                            rsi=rsi_val, atr=atr_val, time=time.time()
                        )

                # --- Save buffers back ---
                self.close_prices[timeframe] = buffer_c
                self.high_prices[timeframe] = buffer_h
                self.low_prices[timeframe] = buffer_l

            # -------------------------------
            # 3️⃣ Mark engine as ready
            # -------------------------------
            if not self.ready and self.close_prices:
                self.ready = True
                LOGGER.info(f"{self.name}: is ready to use...")

    async def postpare(self) -> None:
        """
        Cleanup resources when the engine stops.

        Closes the Redis subscriber and optionally clears buffers or other resources.
        Should be called after `execute()` finishes.
        """
        if self.monitor:
            await self.monitor.close()

        self.close_prices.clear()
        self.subscribed_periods.clear()
        self.current_candle.clear()
        self.ready = False

    async def subscribe(
        self,
        period: int = 14,
        timeframe: str = "1m",
    ):
        """
        Subscribe to a new RSI period and timeframe.

        Args:
            manager: Manager instance used to subscribe to market data streams.
            period: RSI period to calculate.
            timeframe: Candle timeframe (e.g., "1m", "5m").

        Behavior:
            - Pushes a subscription command into the engine's command queue.
            - Ensures the market data stream is subscribed via the manager.
            - Returns the parent subscription response.
        """
        # Push dynamic subscription command to engine queue
        self.command_queue.put(
            {"action": "subscribe", "period": period, "timeframe": timeframe}
        )

        # send back the key of RSIModel
        return f"{self.exchange.value}_{self.market.value}_{timeframe}_{period}"

    @log_exception()
    async def bootstrap_buffer(self, timeframe: str):
        """
        Bootstrap the high, low, and close buffers for a given timeframe by fetching
        historical candles and aligning with the first websocket message.

        Also initializes RSIModel entries in Redis for all currently subscribed periods,
        storing both RSI and ATR values.
        """

        # -------------------------------
        # 1️⃣ Fetch historical candles
        # -------------------------------
        candles = self.info.candle_snapshot(
            market=self.market, timeframe=timeframe, period=500
        )
        closes = np.array(
            [float(c["c"]) for c in candles[-self.data_length :]], dtype=np.float64
        )
        highs = np.array(
            [float(c["h"]) for c in candles[-self.data_length :]], dtype=np.float64
        )
        lows = np.array(
            [float(c["l"]) for c in candles[-self.data_length :]], dtype=np.float64
        )
        timestamps = [int(c["t"]) for c in candles]

        self.close_prices[timeframe] = closes
        self.high_prices[timeframe] = highs
        self.low_prices[timeframe] = lows
        self.current_candle[timeframe] = timestamps[-1]

        LOGGER.info(
            f"[Bootstrap] {self.market} {timeframe} buffer initialized "
            f"({len(closes)} closes), last candle @ {self.current_candle[timeframe]}"
        )

        # -------------------------------
        # 2️⃣ Align with first WebSocket candle
        # -------------------------------
        while True:
            msg = await self.monitor.get_last_message()
            if msg and "i" in msg["data"]:
                ws_time = int(msg["data"]["t"])
                ws_close = float(msg["data"]["c"])
                snap_time = self.current_candle[timeframe]

                if ws_time == snap_time:
                    closes[-1] = ws_close
                elif ws_time > snap_time:
                    closes = np.roll(closes, -1)
                    closes[-1] = ws_close
                    self.current_candle[timeframe] = ws_time
                else:
                    LOGGER.warning(
                        f"[Bootstrap] WS candle behind snapshot ({ws_time} < {snap_time}) ignored"
                    )
                break

        self.close_prices[timeframe] = closes

        # -------------------------------
        # 3️⃣ Pre-create Redis models with RSI & ATR
        # -------------------------------
        for period in self.subscribed_periods.get(timeframe, []):
            pk = f"{self.exchange.value}_{self.market.value}_{timeframe}_{period}"
            try:
                await RSIModel.get_by_id(pk)
            except NotFoundError:
                rsi_val = round(_rsi_numba(closes, period), 2)
                atr_val = _atr_numba(
                    highs, lows, closes, period
                )  # compute ATR from historical candles

                rsi_model = await RSIModel.create(
                    pk=pk,
                    exchange=self.exchange,
                    market=self.market,
                    timeframe=timeframe,
                    period=period,
                    rsi=rsi_val,
                    atr=atr_val,
                    time=time.time(),
                )
                await rsi_model.save()


@njit
def _rsi_numba(prices: np.ndarray, period: int = 14) -> Union[float, Any]:
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


@njit
def _atr_numba(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14
) -> float:
    tr = np.zeros(len(highs))
    for i in range(1, len(highs)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr[i] = max(hl, hc, lc)
    atr = np.mean(tr[1 : period + 1])
    for i in range(period + 1, len(highs)):
        atr = (atr * (period - 1) + tr[i]) / period
    return atr
