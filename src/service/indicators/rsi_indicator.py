import asyncio
import logging
import time
import numpy as np
from numba import njit
from datetime import datetime
from typing import Any, Dict, Union
from fifi import RedisSubscriber, log_exception

from .base import BaseIndicator
from ...enums.exchange import Exchange
from ...enums.market import Market
from ...enums.data_type import DataType
from ...models.rsi_model import RSIModel


LOGGER = logging.getLogger(__name__)


class RSIIndicator(BaseIndicator):
    indicator_name: str = "rsi"
    data_length: int = 14
    monitor: RedisSubscriber
    close_prices: np.ndarray
    last_trade: Dict[str, float] = {}
    rsi_model: RSIModel

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
        self.rsi_model = await RSIModel.create(
            pk=self.pk, exchange=self.exchange, market=self.market, rsi=0, time=0
        )
        await self.rsi_model.save()
        LOGGER.info(f"saved rsi model: {self.rsi_model.dict()}")

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
                await asyncio.sleep(1)
                continue
            rsi = self._rsi_calc()
            await self.rsi_model.update(rsi=rsi, time=time.time())
            LOGGER.info(f"update rsi model: {self.rsi_model.dict()}")

    async def postpare(self) -> None:
        pass

    async def get_last_trade(self) -> Dict[str, float]:
        last_trade = await self.monitor.get_last_message()
        LOGGER.info(last_trade)
        if last_trade:
            if last_trade["type"] == DataType.TRADES.value:
                self.last_trade = last_trade["data"]
        return self.last_trade

    def _rsi_calc(self) -> Union[float, Any]:
        deltas = np.diff(self.close_prices)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        avg_gain = np.mean(gains[: self.data_length])
        avg_loss = np.mean(losses[: self.data_length])

        for i in range(self.data_length, len(deltas)):
            avg_gain = (avg_gain * (self.data_length - 1) + gains[i]) / self.data_length
            avg_loss = (
                avg_loss * (self.data_length - 1) + losses[i]
            ) / self.data_length
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))


#
# @njit
# def _rsi_numba(prices: np.ndarray, period: int = 14) -> Union[float, Any]:
#     deltas = np.diff(prices)
#     gains = np.where(deltas > 0, deltas, 0.0)
#     losses = np.where(deltas < 0, -deltas, 0.0)
#
#     avg_gain = np.mean(gains[:period])
#     avg_loss = np.mean(losses[:period])
#
#     for i in range(period, len(deltas)):
#         avg_gain = (avg_gain * (period - 1) + gains[i]) / period
#         avg_loss = (avg_loss * (period - 1) + losses[i]) / period
#
#     if avg_loss == 0:
#         return 100.0
#
#     rs = avg_gain / avg_loss
#     return 100 - (100 / (1 + rs))
