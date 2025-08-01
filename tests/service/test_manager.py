import pytest
from unittest.mock import patch
from fifi import GetLogger

from src.enums.exchange import Exchange
from src.enums.market import Market
from src.enums.data_type import DataType
from src.service.exchanges.hyperliquid_exchange_worker import HyperliquidExchangeWorker
from src.service.manager import Manager

LOGGER = GetLogger().get()


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
