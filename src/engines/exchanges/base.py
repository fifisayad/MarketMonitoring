from abc import ABC, abstractmethod
from typing import List

from fifi.enums import Exchange, Market
from fifi import MarketDataRepository
from fifi.repository.shm.market_data_repository import intervals_type


class BaseExchangeWorker(ABC):
    exchange: Exchange
    market: Market
    intervals: List[intervals_type]
    _repo: MarketDataRepository
    last_update_timestamp: float

    def __init__(self, market: Market):
        self.market = market

    @abstractmethod
    def ignite(self):
        """start exchange worker engine procedure"""
        pass

    @abstractmethod
    def shutdown(self):
        """Cleanup tasks and shutdown logic"""
        pass
