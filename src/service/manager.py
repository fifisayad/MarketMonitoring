import asyncio
import time
import threading
import logging
from typing import Dict
from fifi import log_exception, singleton

from .indicators.base import BaseIndicator
from .indicators.indicator_factory import create_indicator
from ..common.settings import Settings
from .exchanges.exchange_worker_factory import create_exchange_worker
from ..enums.data_type import DataType
from ..enums.exchange import Exchange
from ..enums.market import Market
from .exchanges.base import BaseExchangeWorker


LOGGER = logging.getLogger(__name__)


@singleton
class Manager:
    exchange_workers: Dict[Exchange, Dict[Market, BaseExchangeWorker]]
    indactor_engines: Dict[Exchange, Dict[Market, BaseIndicator]]

    def __init__(self):
        self.exchange_workers = dict()
        self.indactor_engines = dict()
        self.settings = Settings()
        self.loop = None
        self.thread = None

    async def subscribe(
        self, exchange: Exchange, market: Market, data_type: DataType
    ) -> str:
        if data_type in [DataType.ORDERBOOK, DataType.TRADES]:
            return await self.exchange_worker_subscribe(
                exchange=exchange, market=market, data_type=data_type
            )
        elif data_type in [DataType.RSI, DataType.MACD]:
            return await self.indicator_subscribe(
                exchange=exchange, market=market, data_type=data_type
            )
        else:
            return ""

    async def indicator_subscribe(
        self, exchange: Exchange, market: Market, data_type: DataType
    ) -> str:
        data_channel = await self.exchange_worker_subscribe(
            exchange=exchange, market=market, data_type=DataType.TRADES
        )
        market_indicator = self.indactor_engines.get(exchange)
        indicator_engine = market_indicator.get(market) if market_indicator else None
        if indicator_engine is None:
            indicator_engine = create_indicator(
                exchange=exchange, market=market, data_type=data_type
            )
            await indicator_engine.start()
            if market_indicator:
                self.indactor_engines[exchange][market] = indicator_engine
            else:
                self.indactor_engines[exchange] = {market: indicator_engine}
        return await indicator_engine.subscribe()

    async def exchange_worker_subscribe(
        self, exchange: Exchange, market: Market, data_type: DataType
    ) -> str:
        market_workers = self.exchange_workers.get(exchange)
        worker = market_workers.get(market) if market_workers else None
        if worker is None:
            worker = create_exchange_worker(exchange=exchange, market=market)
            await worker.start()
            if market_workers:
                self.exchange_workers[exchange][market] = worker
            else:
                self.exchange_workers[exchange] = {market: worker}

        await worker.subscribe(data_type)
        return worker.channel

    @log_exception()
    async def stop(self) -> None:
        # Stop event loop
        def shutdown_loop():
            if self.loop:
                self.loop.stop()

        if self.loop:
            self.loop.call_soon_threadsafe(shutdown_loop)

        # stop indactor enignes
        for exchange in self.indactor_engines.keys():
            for market, engine in self.indactor_engines[exchange].items():
                await engine.stop()

        # stop worker exchanges
        for exchange in self.exchange_workers.keys():
            for market, worker in self.exchange_workers[exchange].items():
                await worker.stop()

        LOGGER.info("shutting down manager...")
        if self.thread:
            self.thread.join()

    @log_exception()
    async def start_watcher(self) -> None:
        self.loop = asyncio.new_event_loop()
        # Start the asyncio loop in a separate thread
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

        # Schedule the redis_publisher coroutine on the loop
        asyncio.run_coroutine_threadsafe(self.watcher(), self.loop)

    @log_exception()
    async def watcher(self) -> None:
        LOGGER.info("starting manager watcher....")
        while True:
            await asyncio.sleep(self.settings.RESTART_TIME_THRESHOLD)
            for ex, market_worker in self.exchange_workers.items():
                for market, worker in market_worker.items():
                    if (
                        time.time() - worker.last_update_timestamp
                        > self.settings.RESTART_TIME_THRESHOLD
                    ):
                        await self.restart_ex_worker(
                            ex=ex, market=market, worker=worker
                        )

    async def restart_ex_worker(
        self, ex: Exchange, market: Market, worker: BaseExchangeWorker
    ) -> None:
        LOGGER.info(f"restarting {worker.channel} worker....")
        await worker.stop()
        new_worker = create_exchange_worker(exchange=ex, market=market)
        try:
            await new_worker.start()
            self.exchange_workers[ex][market] = new_worker
            for dt in worker.data_types:
                await new_worker.subscribe(data_type=dt)
            del worker
        except:
            del new_worker
