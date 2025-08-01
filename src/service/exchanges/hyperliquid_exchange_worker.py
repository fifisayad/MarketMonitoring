from hyperliquid.info import Info
from .base import BaseExchangeWorker
from ...enums.exchange import Exchange
from ...enums.market import Market
from ...enums.data_type import DataType
from ...common.settings import Settings


class HyperliquidExchangeWorker(BaseExchangeWorker):
    exchange = Exchange.HYPERLIQUID
    base_url: str
    info: Info

    def __init__(self, market: Market):
        super().__init__(market)
        self.settings = Settings()
        self.base_url = self.settings.HYPERLIQUID_BASE_URL

    async def start(self):
        self.info = Info(self.base_url)

    async def subscribe(self, data_type: DataType):
        if self.is_data_type_subscribed(data_type):
            return

        return await super().subscribe(data_type)

    async def publish(self):
        return await super().publish()

    async def stop(self):
        return await super().stop()
