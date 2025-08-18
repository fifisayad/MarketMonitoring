import asyncio
import time
import numpy as np
from numba import njit
from datetime import datetime
from typing import Dict
from fifi import RedisSubscriber, log_exception

from .base import BaseIndicator
from ...enums.exchange import Exchange
from ...enums.market import Market
from ...enums.data_type import DataType
from ...models.macd_model import MACDModel


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
        self.close_prices = np.arange(self.data_length, dtype=np.float64)

    @log_exception()
    async def prepare(self) -> None:
        # setup redis subscriber for monitor
        self.monitor = await RedisSubscriber.create(channel=self.monitor_channel)
        while not self.last_trade:
            await asyncio.sleep(0.5)
            await self.get_last_trade()

        # redis hash model for rsi
        self.rsi_model = await MACDModel.create(
            pk=self.pk,
            exchange=self.exchange,
            market=self.market,
            macd=0,
            signal=0,
            histogram=0,
            time=0,
        )
        await self.rsi_model.save()

    @log_exception()
    async def execute(self) -> None:
        last_minute = datetime.fromtimestamp(self.last_trade["time"]).minute
        last_price = self.last_trade["price"]
        while True:
            await self.get_last_trade()
            current_minute = datetime.fromtimestamp(self.last_trade["time"]).minute
            if current_minute != last_minute:
                if len(self.close_prices) == self.data_length:
                    self.close_prices = np.roll(self.close_prices, -1)
                self.close_prices[-1] = last_price
            else:
                last_price = self.last_trade["price"]
                last_minute = current_minute
                continue
            macd, signal, histogram = _macd_numba(self.close_prices)
            await self.rsi_model.update(
                macd=macd, signal=signal, histogram=histogram, time=time.time()
            )

    async def postpare(self) -> None:
        pass

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
