from typing import Dict
from fifi import singleton

from .exchanges.exchange_factory import create_exchange_worker
from ..enums.data_type import DataType
from ..enums.exchange import Exchange
from ..enums.market import Market
from .exchanges.base import BaseExchangeWorker


@singleton
class Manager:
    exchange_workers: Dict[Exchange, Dict[Market, BaseExchangeWorker]]

    def __init__(self):
        self.exchange_workers = dict()

    async def subscribe(
        self, exchange: Exchange, market: Market, data_type: DataType
    ) -> str:
        market_workers = self.exchange_workers.get(exchange)
        worker = market_workers.get(market) if market_workers else None
        if worker is None:
            worker = create_exchange_worker(exchange=exchange, market=market)
            await worker.start()
            self.exchange_workers[exchange][market] = worker
        await worker.subscribe(data_type)
        return worker.channel
