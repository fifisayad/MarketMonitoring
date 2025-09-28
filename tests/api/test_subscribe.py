from fifi.helpers.get_logger import LoggerFactory
from fifi.schema import MarketSubscriptionRequestSchema, SubscriptionResponseSchema
from fifi.enums import DataType, Exchange, Market

import pytest
from unittest.mock import patch, Mock
from httpx import ASGITransport, AsyncClient
from main import app
from fastapi.encoders import jsonable_encoder

from src.service.exchanges.hyperliquid_exchange_worker import HyperliquidExchangeWorker

LOGGER = LoggerFactory().get(__name__)


@pytest.mark.anyio
@patch.object(HyperliquidExchangeWorker, "subscribe", return_value=None)
@patch.object(HyperliquidExchangeWorker, "start", return_value=None)
async def test_subscription(start: Mock, subscribe: Mock):
    body_schema = MarketSubscriptionRequestSchema(
        exchange=Exchange.HYPERLIQUID, market=Market.BTCUSD, data_type=DataType.TRADES
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/subscribe", json=jsonable_encoder(body_schema))
    assert response.status_code == 200
    response_schema = SubscriptionResponseSchema(
        channel=f"{Exchange.HYPERLIQUID.value}_{Market.BTCUSD.value}"
    )
    LOGGER.info(f"response: {response.json()}")

    assert response.json() == jsonable_encoder(response_schema)
