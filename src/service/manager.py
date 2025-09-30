import time
import asyncio
import threading

from typing import Dict

from fifi import log_exception, singleton
from fifi.helpers.get_logger import LoggerFactory
from fifi.enums import Exchange, Market, DataType, IndicatorType

from ..common.settings import Settings
from .indicators.base import BaseIndicator
from .indicators.indicator_factory import create_indicator_worker
from .exchanges.exchange_worker_factory import create_exchange_worker
from .exchanges.base import BaseExchangeWorker


LOGGER = LoggerFactory().get(__name__)


@singleton
class Manager:
    exchange_workers: Dict[Exchange, Dict[Market, BaseExchangeWorker]]
    indactor_engines: Dict[Exchange, Dict[Market, Dict[IndicatorType, BaseIndicator]]]

    def __init__(self):
        self.exchange_workers = dict()
        self.indactor_engines = dict()
        self.settings = Settings()
        self.loop = None
        self.thread = None

    async def subscribe(
        self,
        exchange: Exchange,
        market: Market,
        data_type: DataType,
        **kwargs,
    ) -> str:
        if data_type in DataType:
            return await self.exchange_worker_subscribe(
                exchange=exchange,
                market=market,
                data_type=data_type,
                **kwargs,
            )
        elif data_type in IndicatorType:
            return await self.indicator_subscribe(
                exchange=exchange,
                market=market,
                data_type=data_type,
                **kwargs,
            )
        else:
            return ""

    async def indicator_subscribe(
        self,
        exchange: Exchange,
        market: Market,
        data_type: IndicatorType,
        **kwargs,
    ) -> str:
        await self.exchange_worker_subscribe(
            exchange,
            market,
            DataType.CANDLE,
            **kwargs,
        )
        market_indicator = self.indactor_engines.get(exchange)
        indicator = market_indicator.get(market) if market_indicator else None
        worker = indicator.get(data_type) if indicator else None
        if worker is None:
            worker = create_indicator_worker(
                exchange=exchange,
                market=market,
                data_type=data_type,
            )
            await worker.start()
            if indicator:
                self.indactor_engines[exchange][market][data_type] = worker
            else:
                if market_indicator:
                    self.indactor_engines[exchange][market] = {data_type: worker}
                else:
                    self.indactor_engines[exchange] = {market: {data_type: worker}}

        return await worker.subscribe(**kwargs)

    async def exchange_worker_subscribe(
        self,
        exchange: Exchange,
        market: Market,
        data_type: DataType,
        **kwargs,
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

        await worker.subscribe(data_type, **kwargs)
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
            for market, indicator in self.indactor_engines[exchange].items():
                for data_type, engine in indicator.items():
                    await engine.stop()

        # stop worker exchanges
        for exchange in self.exchange_workers.keys():
            for market, worker in self.exchange_workers[exchange].items():
                await worker.stop()

        LOGGER.info("shutting down manager...")
        if self.thread:
            self.thread.join()

    async def start_watcher(self) -> None:
        """
        Start the watcher in a separate thread and loop.
        It periodically checks all exchange workers and restarts them if needed.
        """
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

        # Schedule the watcher coroutine on this loop
        asyncio.run_coroutine_threadsafe(self.watcher(), self.loop)

    @log_exception()
    async def watcher(self) -> None:
        """
        Periodically checks exchange workers for stale connections and restarts them.
        """
        LOGGER.info("Starting manager watcher...")

        while True:
            await asyncio.sleep(self.settings.RESTART_TIME_THRESHOLD)

            for ex, market_workers in self.exchange_workers.items():
                for market, worker in market_workers.items():
                    if (
                        time.time() - worker.last_update_timestamp
                        > self.settings.RESTART_TIME_THRESHOLD
                    ):
                        await self.restart_ex_worker(
                            ex=ex, market=market, worker=worker
                        )

    @log_exception()
    async def restart_ex_worker(
        self, ex: Exchange, market: Market, worker: BaseExchangeWorker
    ) -> None:
        """
        Restart a worker and resubscribe all its previous subscriptions.
        """
        LOGGER.info(f"Restarting {worker.channel} worker...")

        # Stop old worker
        await worker.stop()

        # Create and start a new worker
        new_worker = create_exchange_worker(exchange=ex, market=market)
        try:
            await new_worker.start()
            self.exchange_workers[ex][market] = new_worker

            # Resubscribe all previous subscriptions with stored kwargs
            for sub in getattr(worker, "subscriptions", []):
                await new_worker.subscribe(**sub)

        finally:
            del worker
