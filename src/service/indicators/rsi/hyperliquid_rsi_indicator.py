import asyncio
import logging
import time
import numpy as np

from numba import njit
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from fifi import RedisSubscriber, log_exception

from ..base import BaseIndicator
from ....enums.exchange import Exchange
from ....enums.market import Market
from ....enums.data_type import DataType
from ....models.rsi_model import RSIModel
from ....helpers.hyperliquid_helpers import *
from ...info.hyperliquid_info import HyperliquidInfo
from ...manager import Manager

LOGGER = logging.getLogger(__name__)


class HyperLiquidRSIIndicator(BaseIndicator):
    indicator_name: str = "rsi"
    data_length: int = 200
    monitor: RedisSubscriber
    close_prices: np.ndarray
    last_trade: Dict[str, float] = {}
    rsi_model: RSIModel

    def __init__(
        self,
        exchange: Exchange,
        market: Market,
        period: int = 14,
        timeframe: str = "1m",
    ):
        super().__init__(exchange=exchange, market=market, run_in_process=True)
        self.period = period
        self.timeframe = timeframe
        self.monitor_channel = f"{self.exchange.value}_{self.market.value}"
        self.indicator_workers = dict()

    @log_exception()
    async def prepare(self) -> None:
        self.info = HyperliquidInfo()
        candles = self.info.candle_snapshot(
            name=market_to_hyper_market(Market.BTCUSD_PERP),
            interval=self.timeframe,
        )
        candles_length = len(candles)
        self.close_prices = np.arange(self.data_length, dtype=np.float64)
        for i in range(self.data_length):
            self.close_prices[i] = float(
                candles[candles_length - self.data_length + i]["c"]
            )

        # setup redis subscriber for monitor
        exchange_worker_manager = Manager()
        exchange_worker_manager.subscribe(self.exchange, self.market, DataType.CANDLE1M)
        self.monitor = await RedisSubscriber.create(channel=self.monitor_channel)

        # redis hash model for rsi
        self.rsi_model = await RSIModel.create(
            pk=self.pk, exchange=self.exchange, market=self.market, rsi=0, time=0
        )
        await self.rsi_model.save()

    @log_exception()
    async def execute(self) -> None:
        while True:
            msg = await self.monitor.get_last_message()
            if msg:
                if msg["channel"] == "candle":
                    if self.current_candle != float(msg["data"]["t"]):
                        self.current_rsi = _rsi_numba(
                            self.close_prices, period=self.rsi_period
                        )
                        self.close_prices = np.roll(self.close_prices, -1)
                        self.current_candle = float(msg["data"]["t"])
                    self.close_prices[-1] = float(msg["data"]["c"])
            if not self.ready:
                self.ready = True
                LOGGER.info(f"{self.name}: is ready to use...")

    async def postpare(self) -> None:
        self.monitor.close()


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
