import sys, signal
import time
from typing import Dict

from fifi import MonitoringSHMRepository
from fifi.helpers.get_logger import LoggerFactory
from fifi.enums import Market

from ..common.settings import Settings
from .exchanges.exchange_worker_factory import create_exchange_worker
from .exchanges.base import BaseExchangeWorker
from .indicators.indicator_engine import IndicatorEngine


LOGGER = LoggerFactory().get(__name__)

shutdown_flag = False


def handle_signal(signum, frame):
    global shutdown_flag
    print(f"Received signal {signum}, shutting down gracefully...")
    shutdown_flag = True


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
            self.indactor_engines[market].start()

        self.watch()

    def watch(self):
        # Register handlers for SIGTERM (docker stop) and SIGINT (Ctrl+C)
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
        try:
            while not shutdown_flag:
                # Your main loop logic
                time.sleep(5)
        except Exception as e:
            LOGGER.error(f"Error: {e}")
        finally:
            LOGGER.info("Cleanup before exit...")
            LOGGER.info("closing shared memory repo...")
            self.monitor_repo.close()
            print("Exited cleanly.")
