from .base import BaseExchangeWorker
from fifi.enums import Exchange, Market
from fifi import MonitoringSHMRepository


class BinanceExchangeWorker(BaseExchangeWorker):
    exchange = Exchange.BINANCE

    def __init__(self, market: Market, monitoring_repo: MonitoringSHMRepository):
        super().__init__(market, monitoring_repo)

    def start(self):
        return super().start()

    def stop(self):
        return super().stop()
