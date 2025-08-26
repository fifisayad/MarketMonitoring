import asyncio
import logging
import time
from hyperliquid.info import Info
import numpy as np
from numba import njit
from datetime import datetime
from typing import Any, Dict, List, Optional
from fifi import RedisSubscriber, log_exception

from .base import BaseIndicator
from ...enums.exchange import Exchange
from ...enums.market import Market
from ...enums.data_type import DataType
from ...models.sma_model import SMAModel
from ...helpers.hyperliquid_helpers import *


LOGGER = logging.getLogger(__name__)


class SMAIndicator(BaseIndicator):
    indicator_name: str = "sma"
    data_length: int = 30
    monitor: RedisSubscriber
    close_prices: np.ndarray
    last_trade: Dict[str, float] = {}
    sma_model: SMAModel

    def __init__(self, exchange: Exchange, market: Market):
        super().__init__(exchange=exchange, market=market, run_in_process=True)
        self.monitor_channel = f"{self.exchange.value}_{self.market.value}"
        self.base_url = self.settings.HYPERLIQUID_BASE_URL

    @log_exception()
    async def prepare(self) -> None:
        self.info = Info(self.base_url)
        now_ms = int(time.time() * 1000)
        minutes_ago_ms = now_ms - (200 * 60 * 1000)
        candles = self.info.candles_snapshot(
            name=market_to_hyper_market(Market.BTCUSD_PERP),
            interval="1m",
            startTime=minutes_ago_ms,
            endTime=now_ms,
        )
        self.info.disconnect_websocket()

        candles_length = len(candles)
        self.close_prices = np.arange(self.data_length, dtype=np.float64)
        for i in range(self.data_length):
            self.close_prices[i] = float(
                candles[candles_length - self.data_length + i]["c"]
            )

        # setup redis subscriber for monitor
        self.monitor = await RedisSubscriber.create(channel=self.monitor_channel)
        while not self.last_trade:
            await asyncio.sleep(0.5)
            await self.get_last_trade()

        # redis hash model for rsi
        self.sma_model = await SMAModel.create(
            pk=self.pk,
            exchange=self.exchange,
            market=self.market,
            sma=0,
            slope=0,
            time=0,
        )
        await self.sma_model.save()

    @log_exception()
    async def execute(self) -> None:
        last_minute = datetime.fromtimestamp(self.last_trade["time"]).minute
        last_price = self.last_trade["price"]
        while True:
            trades = await self.get_last_trades()
            if trades is None:
                continue
            for trade in trades:
                if trade["type"] == DataType.TRADES.value:
                    data = trade["data"]
                    current_minute = datetime.fromtimestamp(data["time"]).minute
                    if current_minute != last_minute:
                        self.close_prices = np.roll(self.close_prices, -1)
                        self.close_prices[-1] = last_price
                        last_minute = current_minute
                    else:
                        last_price = data["price"]
                        self.close_prices[-1] = last_price
                    smas = simple_moving_average(self.close_prices, window=10)
                    slopes = regression_slope(smas, window=10)
                    slope_segments = detect_slope_segments(slopes)
                    if smas is None or slopes is None:
                        continue
                    await self.sma_model.update(
                        sma=float(smas[-1]),
                        slope=float(slope_segments[-1][-1]),
                        time=time.time(),
                    )

    async def postpare(self) -> None:
        pass

    async def get_last_trades(self) -> Optional[List[Any]]:
        return await self.monitor.get_messages()

    async def get_last_trade(self) -> Dict[str, float]:
        last_trade = await self.monitor.get_last_message()
        if last_trade:
            if last_trade["type"] == DataType.TRADES.value:
                self.last_trade = last_trade["data"]
        return self.last_trade


@njit
def simple_moving_average(arr, window):
    n = len(arr)
    if window > n:
        return None

    result = np.empty(n - window + 1, dtype=np.float64)
    cumsum = 0.0

    # Initial window sum
    for i in range(window):
        cumsum += arr[i]
    result[0] = cumsum / window

    # Sliding window
    for i in range(window, n):
        cumsum += arr[i] - arr[i - window]
        result[i - window + 1] = cumsum / window

    return result


@njit
def regression_slope(series, window):
    n = len(series)
    if window > n:
        return None

    slopes = np.empty(n - window + 1, dtype=np.float64)

    # Precompute x values and mean
    x = np.arange(window, dtype=np.float64)
    x_mean = np.mean(x)
    denom = np.sum((x - x_mean) ** 2)

    for i in range(n - window + 1):
        y = series[i : i + window]
        y_mean = np.mean(y)
        numer = 0.0
        for j in range(window):
            numer += (x[j] - x_mean) * (y[j] - y_mean)
        slopes[i] = numer / denom

    return slopes


@njit
def detect_slope_segments(slopes, tol=1e-6):
    """
    Groups slopes into segments where direction is consistent.
    Returns segments with average slope for each.
    Each segment: (start_index, end_index, avg_slope)
    """
    if len(slopes) == 0:
        return np.empty((0, 3), dtype=np.float64)

    segments = []
    start = 0
    current_slope = slopes[0]

    for i in range(1, len(slopes)):
        if (slopes[i] * current_slope < 0) or (abs(slopes[i] - current_slope) > tol):
            # End segment → compute average slope
            avg_slope = np.mean(slopes[start:i])
            segments.append((start, i - 1, avg_slope))

            # Start new segment
            start = i
            current_slope = slopes[i]

    # Add final segment
    avg_slope = np.mean(slopes[start:])
    segments.append((start, len(slopes) - 1, avg_slope))

    return np.array(segments, dtype=np.float64)
