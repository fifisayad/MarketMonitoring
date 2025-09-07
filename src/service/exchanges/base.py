from abc import ABC, abstractmethod
from typing import Set

from fifi import RedisPublisher

from ...enums.data_type import DataType
from ...enums.exchange import Exchange
from ...enums.market import Market


class BaseExchangeWorker(ABC):
    exchange: Exchange
    market: Market
    data_types: Set[DataType]
    channel: str
    redis_publisher: RedisPublisher
    last_update_timestamp: float

    def __init__(self, market: Market):
        self.market = market
        self.channel = f"{self.exchange.value}_{self.market.value}"
        self.data_types = set()
        self.subscriptions: list[dict] = []

    @abstractmethod
    async def start(self):
        """Establish WebSocket connection"""
        pass

    @abstractmethod
    async def publish(self):
        """Listen to incoming data and publish to Redis"""
        pass

    @abstractmethod
    async def subscribe(self, data_type: DataType):
        """subscribe new data type"""
        pass

    @abstractmethod
    async def stop(self):
        """Cleanup tasks and shutdown logic"""
        pass

    def is_data_type_subscribed(self, data_type: DataType, **kwargs) -> bool:
        # optionally check if same data_type + interval already subscribed
        if data_type != DataType.CANDLE:
            return data_type in self.data_types

        # for candles, check if same timeframe already subscribed
        timeframe = kwargs.get("timeframe")
        return any(
            sub["data_type"] == DataType.CANDLE and sub.get("timeframe") == timeframe
            for sub in getattr(self, "subscriptions", [])
        )
