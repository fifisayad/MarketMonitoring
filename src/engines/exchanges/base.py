from abc import ABC, abstractmethod
from typing import Set

from fifi.enums import Exchange, Market, DataType
from fifi import MonitoringSHMRepository


class BaseExchangeWorker(ABC):
    exchange: Exchange
    market: Market
    data_types: Set[DataType]
    monitoring_repo: MonitoringSHMRepository
    last_update_timestamp: float

    def __init__(self, market: Market, monitoring_repo: MonitoringSHMRepository):
        self.market = market
        self.monitoring_repo = monitoring_repo

    @abstractmethod
    def start(self):
        """Establish WebSocket connection"""
        pass

    @abstractmethod
    def stop(self):
        """Cleanup tasks and shutdown logic"""
        pass
