from .base import BaseExchangeWorker
from fifi.enums import Exchange, Market


class BinanceExchangeWorker(BaseExchangeWorker):
    exchange = Exchange.BINANCE

    def __init__(self, market: Market):
        super().__init__(market)

    def ignite(self):
        return super().ignite()

    def shutdown(self):
        return super().shutdown()
