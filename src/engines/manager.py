from typing import Dict

from fifi import MonitoringSHMRepository
from fifi.helpers.get_logger import LoggerFactory
from fifi.enums import Market

from ..common.settings import Settings
from .exchanges.exchange_worker_factory import create_exchange_worker
from .exchanges.base import BaseExchangeWorker
from .indicators.indicator_engine import IndicatorEngine


LOGGER = LoggerFactory().get(__name__)


class Manager:
    def __init__(self):
        self.exchange_workers: Dict[Market, BaseExchangeWorker] = dict()
        self.indactor_engines: Dict[Market, IndicatorEngine] = dict()
        self.settings = Settings()
        self.monitor_repo = MonitoringSHMRepository(
            create=True, markets=self.settings.MARKETS
        )

    def start(self) -> None:
        LOGGER.info("starting exchange workers for markets.....")
        for market in self.settings.MARKETS:
            self.exchange_workers[market] = create_exchange_worker(
                exchange=self.settings.EXCHANGE,
                market=market,
                monitoring_repo=self.monitor_repo,
            )
            self.exchange_workers[market].start()

        LOGGER.info("starting indicator engines for markets.....")
        for market in self.settings.MARKETS:
            self.indactor_engines[market] = IndicatorEngine(
                market=market, monitor_repo=self.monitor_repo
            )
