import asyncio
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
from ...models.macd_model import MACDModel
from ...helpers.hyperliquid_helpers import *


class MACDIndicator(BaseIndicator):
    indicator_name: str = "macd"
    data_length: int = 200  # this best for smooth and reliable result
    monitor: RedisSubscriber
    close_prices: np.ndarray
    last_trade: Dict[str, float] = {}
    macd_model: MACDModel

    def __init__(self, exchange: Exchange, market: Market):
        super().__init__(exchange=exchange, market=market, run_in_process=True)
        self.monitor_channel = f"{self.exchange.value}_{self.market.value}"
        self.base_url = self.settings.HYPERLIQUID_BASE_URL

    @log_exception()
    async def prepare(self) -> None:
        # initial close prices
        self.info = Info(self.base_url)
        now_ms = int(time.time() * 1000)
        minutes_ago_ms = now_ms - (500 * 60 * 1000)
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
        self.macd_model = await MACDModel.create(
            pk=self.pk,
            exchange=self.exchange,
            market=self.market,
            macd=0,
            signal=0,
            histogram=0,
            time=0,
        )
        await self.macd_model.save()

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
                    macd, signal, histogram = _macd_numba(self.close_prices)
                    await self.macd_model.update(
                        macd=macd, signal=signal, histogram=histogram, time=time.time()
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
def _ema_numba(values: np.ndarray, period: int) -> np.ndarray:
    ema = np.empty(len(values), dtype=np.float64)
    alpha = 2 / (period + 1)
    ema[0] = values[0]
    for i in range(1, len(values)):
        ema[i] = alpha * values[i] + (1 - alpha) * ema[i - 1]
    return ema


@njit
def _macd_numba(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = _ema_numba(prices, fast)
    ema_slow = _ema_numba(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema_numba(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line[-1], signal_line[-1], histogram[-1]
