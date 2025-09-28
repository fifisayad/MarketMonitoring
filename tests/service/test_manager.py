import pytest
import random
from unittest.mock import patch, Mock
from fifi import LoggerFactory
from fifi.enums import Exchange, Market, DataType
from src.service.exchanges.hyperliquid_exchange_worker import HyperliquidExchangeWorker
from src.service.manager import Manager

LOGGER = LoggerFactory("DEBUG").get(__name__)


@pytest.mark.asyncio
class TestManager:
    manager = Manager()

    @patch.object(HyperliquidExchangeWorker, "start", return_value=None)
    @patch.object(HyperliquidExchangeWorker, "subscribe", return_value=None)
    async def test_manager_subscribe(self, start, subscribe):
        assert len(self.manager.exchange_workers) == 0
        channel = await self.manager.subscribe(
            exchange=Exchange.HYPERLIQUID,
            market=Market.BTCUSD,
            data_type=DataType.TRADES,
        )
        assert channel == f"{Exchange.HYPERLIQUID.value}_{Market.BTCUSD.value}"
        assert Exchange.HYPERLIQUID in self.manager.exchange_workers
        assert Market.BTCUSD in self.manager.exchange_workers[Exchange.HYPERLIQUID]
        assert isinstance(
            self.manager.exchange_workers[Exchange.HYPERLIQUID][Market.BTCUSD],
            HyperliquidExchangeWorker,
        )
        start.assert_called_once()
        subscribe.assert_called_once()

    @patch.object(HyperliquidExchangeWorker, "start", return_value=None)
    @patch.object(HyperliquidExchangeWorker, "subscribe", return_value=None)
    @patch.object(HyperliquidExchangeWorker, "stop", return_value=None)
    async def test_manager_stop(self, stop: Mock, subscribe: Mock, start: Mock):
        for i in range(5):
            channel = await self.manager.subscribe(
                exchange=Exchange.HYPERLIQUID,
                market=random.choice(
                    [
                        Market.BTCUSD,
                        Market.BTCUSD_PERP,
                        Market.ETHUSD,
                        Market.ETHUSD_PERP,
                    ]
                ),
                data_type=random.choice([DataType.TRADES, DataType.ORDERBOOK]),
            )
        worker_counts = 0
        for exchange in self.manager.exchange_workers:
            for market, worker in self.manager.exchange_workers[exchange].items():
                assert worker.channel == f"{exchange.value}_{market.value}"
                assert isinstance(worker, HyperliquidExchangeWorker)
                worker_counts += 1

        assert start.call_count == worker_counts - 1
        assert subscribe.call_count == 5

        await self.manager.stop()
        assert stop.call_count == worker_counts
