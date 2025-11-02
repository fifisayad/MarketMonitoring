from abc import ABC, abstractmethod
from typing import List
from multiprocessing.synchronize import Event as EventType
from multiprocessing import Event

from fifi.enums import Exchange, Market
from fifi import MarketDataRepository
from fifi.repository.shm.market_data_repository import intervals_type


class BaseExchangeWorker(ABC):
    exchange: Exchange
    market: Market
    intervals: List[intervals_type]
    _repo: MarketDataRepository
    last_update_timestamp: float
    shutdown_event: EventType

    def __init__(self, market: Market):
        self.market = market
        self.shutdown_event = Event()

    @abstractmethod
    def ignite(self):
        """start exchange worker engine procedure"""
        pass

    @abstractmethod
    def shutdown(self):
        """Cleanup tasks and shutdown logic"""
        pass
