import asyncio
from typing import Literal, Union, overload
from hyperliquid.info import Info
from fifi import RedisPublisher
from .base import BaseExchangeWorker
from ...enums.exchange import Exchange
from ...enums.market import Market
from ...enums.data_type import DataType
from ...common.settings import Settings


def data_type_to_type(
    data_type: DataType,
) -> str:
    if data_type == DataType.TRADES:
        return "trades"
    elif data_type == DataType.ORDERBOOK:
        return "l2Book"
    else:
        raise ValueError(f"there is no data type fo {data_type.value} in hyperliquid")


def market_to_hyper_market(market: Market) -> str:
    second_coin = market.value[:3]
    first_coin = market.value[3:]
    return f"{first_coin.upper()}/{second_coin.upper()}"


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
        self.redis_publisher = await RedisPublisher.create(channel=self.channel)

    async def subscribe(self, data_type: DataType):
        if self.is_data_type_subscribed(data_type):
            return
        self.info.subscribe(
            {  # type: ignore
                "type": f"{data_type_to_type(data_type)}",
                "coin": f"{market_to_hyper_market(self.market)}",
            },
            self.publish_sync,
        )

    def publish_sync(self, msg: str):
        asyncio.create_task(self.publish(msg))

    async def publish(self, msg: str):
        await self.redis_publisher.publish(msg)

    async def stop(self):
        return await super().stop()
