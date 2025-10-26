import asyncio
from fifi import BaseEngine, MonitoringSHMRepository, log_exception, LoggerFactory
from fifi.enums import Market, MarketStat

from ...common.settings import Settings
from .calcs.rsi import _rsi_numba
from .calcs.atr import _atr_numba
from .calcs.hma import _hma_numba

LOGGER = LoggerFactory().get(__name__)


class IndicatorEngine(BaseEngine):
    market: Market
    indicator_name: str
    name: str
    monitor_repo: MonitoringSHMRepository

    def __init__(
        self,
        market: Market,
        monitor_repo: MonitoringSHMRepository,
        run_in_process: bool = True,
    ):
        super().__init__(run_in_process)
        self.market = market
        self.name = f"{self.market.value}_IndicatorEngine"
        self.settings = Settings()
        self.monitor_repo = monitor_repo
        self.market_row_index = self.monitor_repo.row_index[self.market]
        self.periods = self.settings.INDICATORS_PERIODS

    @log_exception()
    async def prepare(self) -> None:
        while True:
            if self.monitor_repo.is_updated(self.market):
                break
            await asyncio.sleep(1)

    @log_exception()
    async def execute(self) -> None:
        LOGGER.info(f"{self.name} is executing...")
        while True:
            close_prices = self.monitor_repo.get_close_prices(self.market)
            low_prices = self.monitor_repo.get_low_prices(self.market)
            high_prices = self.monitor_repo.get_high_prices(self.market)
            for period in self.periods:
                rsi_val = round(_rsi_numba(close_prices, period), 2)
                atr_val = _atr_numba(high_prices, low_prices, close_prices, period)
                hma_val = _hma_numba(close_prices, 100)  # benchmark value for hma

                self.monitor_repo.set_stat(
                    self.market, MarketStat[f"RSI{period}"], rsi_val
                )
                self.monitor_repo.set_stat(
                    self.market, MarketStat[f"ATR{period}"], atr_val
                )
                self.monitor_repo.set_stat(self.market, MarketStat["HMA"], hma_val)
            await asyncio.sleep(0.01)

    async def postpare(self):
        pass
