import signal
import time
from typing import Dict

from fifi import log_exception
from fifi.helpers.get_logger import LoggerFactory
from fifi.enums import Market

from ..common.settings import Settings
from .exchanges.exchange_worker_factory import create_exchange_worker
from .exchanges.base import BaseExchangeWorker
from .indicators.indicator_engine import IndicatorEngine


LOGGER = LoggerFactory().get("Manager")

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

    @log_exception()
    def start(self) -> None:
        LOGGER.info("starting exchange workers for markets.....")
        for market in self.settings.MARKETS:
            self.exchange_workers[market] = create_exchange_worker(
                exchange=self.settings.EXCHANGE,
                market=market,
            )
            self.exchange_workers[market].start()

        LOGGER.info("starting indicator engines for markets.....")
        for market in self.settings.MARKETS:
            self.indactor_engines[market] = IndicatorEngine(market=market)
            self.indactor_engines[market].start()

        # Register handlers for SIGTERM (docker stop) and SIGINT (Ctrl+C)
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
        try:
            while not shutdown_flag:
                time.sleep(5)
        except Exception as e:
            LOGGER.error(f"Error: {e}")
        finally:
            LOGGER.info("stopping indicator engines....")
            for market, engine in self.indactor_engines.items():
                engine.stop()
            LOGGER.info("stopping exchange workers...")
            for market, ex_worker in self.exchange_workers.items():
                ex_worker.stop()
            LOGGER.info("Exited cleanly.")
