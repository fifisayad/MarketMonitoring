from typing import Dict
from fifi import singleton

from ..enums.data_type import DataType
from ..enums.exchange import Exchange
from ..enums.market import Market
from .exchanges.base import BaseExchangeWorker


@singleton
class Manager:
    exchange_workers: Dict[str, BaseExchangeWorker]

    def __init__(self):
        self.exchange_workers = dict()

    def subscribe(self, exchane: Exchange, market: Market, data_type: DataType) -> str:
        return ""
