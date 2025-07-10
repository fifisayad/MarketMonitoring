import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status

from src.main import app
from src.common.enums import ExchangeEnum, PairEnum
from src.common.schemas import SubscriptionRequest

# Sample test input
valid_payload = {
    "exchange": ExchangeEnum.hyper.value,
    "pair": PairEnum.btcusdt.value,
}

invalid_payload = {"exchange": "invalid_exchange", "pair": "invalid_pair"}


@pytest.mark.asyncio
async def test_subscribe_success():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/subscribe", json=valid_payload)
    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()["msg"]
        == "data channel is started - now you can subscribe to the channel name."
    )
    assert (
        response.json()["result"]
        == f"{valid_payload['exchange']}-{valid_payload['pair']}"
    )


@pytest.mark.asyncio
async def test_subscribe_invalid_exchange():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/subscribe", json=invalid_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
