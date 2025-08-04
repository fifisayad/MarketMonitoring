import os
import asyncio
import pytest
from dotenv import load_dotenv
from fastapi.encoders import jsonable_encoder
from httpx import ASGITransport, AsyncClient
from fifi import RedisSubscriber, GetLogger

from src.common.schemas import SubscriptionRequestSchema
from src.enums.data_type import DataType
from src.enums.exchange import Exchange
from src.enums.market import Market
from main import app

LOGGER = GetLogger().get()
load_dotenv()


@pytest.mark.asyncio
class TestIntegration:

    async def test_getting_hyperliquid_trades(self):
        channel = f"{Exchange.HYPERLIQUID.value}_{Market.BTCUSD_PERP.value}"
        subscribe = await RedisSubscriber.create(channel)
        LOGGER.info(f"REDIS_HOST= {os.getenv("REDIS_HOST", "localhost")}")
        body_schema = SubscriptionRequestSchema(
            exchange=Exchange.HYPERLIQUID,
            market=Market.BTCUSD_PERP,
            data_type=DataType.TRADES,
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post("/subscribe", json=jsonable_encoder(body_schema))

            if response.status_code == 500:
                LOGGER.info(response.json())
            assert response.status_code == 200
            LOGGER.info(f"response: {response.json()}")
            channel = response.json()["channel"]
            assert channel == f"{Exchange.HYPERLIQUID.value}_{Market.BTCUSD_PERP.value}"
            while True:
                await asyncio.sleep(1)
                msg = await subscribe.get_last_message()
                LOGGER.info(f"{msg=}")
                if msg:
                    if msg["type"] == DataType.TRADES.value:
                        break
            subscribe.close()
            await ac.aclose()
