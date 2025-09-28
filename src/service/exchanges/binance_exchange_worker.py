from .base import BaseExchangeWorker
from fifi.enums import Exchange, Market, DataType


class BinanceExchangeWorker(BaseExchangeWorker):
    exchange = Exchange.BINANCE

    def __init__(self, market: Market):
        super().__init__(market)

    async def start(self):
        return await super().start()

    async def subscribe(self, data_type: DataType):
        return await super().subscribe(data_type)

    async def publish(self):
        return await super().publish()

    async def stop(self):
        return await super().stop()
