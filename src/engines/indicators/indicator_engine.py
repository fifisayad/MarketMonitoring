import asyncio
from typing import Dict
from fifi import (
    BaseEngine,
    MarketStatRepository,
    MarketDataRepository,
    log_exception,
    LoggerFactory,
)
from fifi.enums.market import MarketStat
from fifi.enums import Market
from fifi.types.market import intervals_type

from ...common.settings import Settings
from .calcs.rsi import _rsi_numba
from .calcs.atr import _atr_numba
from .calcs.hma import _hma_numba

LOGGER = LoggerFactory().get(__name__)


class IndicatorEngine(BaseEngine):
    market: Market
    indicator_name: str
    name: str
    _repos: Dict[intervals_type, MarketStatRepository]
    _data_repos: Dict[intervals_type, MarketDataRepository]

    def __init__(
        self,
        market: Market,
        run_in_process: bool = True,
    ):
        super().__init__(run_in_process)
        self.market = market
        self.name = f"{self.market.value}_IndicatorEngine"
        self.settings = Settings()
        self._repos = dict()
        self._data_repos = dict()

    @log_exception()
    async def prepare(self) -> None:
        for interval in self.settings.INTERVALS:
            self._repos[interval] = MarketStatRepository(
                market=self.market, interval=interval, create=True
            )
            self._data_repos[interval] = MarketDataRepository(
                market=self.market, interval=interval
            )

    @log_exception()
    async def execute(self) -> None:
        LOGGER.info(f"{self.name} is executing...")
        while True:
            for interval, repo in self._repos.items():
                if self._data_repos[interval].get_time() > repo.get_time():
                    repo.new_row()
                    repo.set_time(self._data_repos[interval].get_time())
                for stat in MarketStat:
                    value = self.get_calc_result(interval, stat)
                    repo.set_last_stat(stat, value)
            await asyncio.sleep(0.1)

    def get_calc_result(self, interval: intervals_type, stat: MarketStat):
        repo = self._data_repos[interval]
        closes = repo.get_closes()
        lows = repo.get_lows()
        highs = repo.get_highs()
        if stat == MarketStat.ATR14:
            return _atr_numba(highs, lows, closes, 14)
        elif stat == MarketStat.RSI14:
            return round(_rsi_numba(closes, 14), 2)
        elif stat == MarketStat.HMA:
            return _hma_numba(closes, 55)
        else:
            return 0

    async def postpare(self):
        for interval, repo in self._repos.items():
            repo.close()
        for interval, repo in self._data_repos.items():
            repo.close()
