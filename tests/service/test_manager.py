import pytest
import pytest_asyncio
import asyncio

from src.service.manager import create_channel
from fifi.redis.redis_subscriber import RedisSubscriber
from fifi.redis.redis_client import RedisClient
from fifi import GetLogger

exchange = "hyper"
pair = "BTCUSDT"
LOGGER = GetLogger().get()
CHANNEL = f"{exchange}-{pair}"


@pytest_asyncio.fixture
async def setup_redis_subscriber():
    LOGGER.info("Creating Redis Subscriber ....")
    subscriber = await RedisSubscriber.create(CHANNEL)
    yield subscriber
    LOGGER.info("Cleaning Redis Subscriber Task ...")
    subscriber.close()


@pytest.mark.redis
@pytest.mark.asyncio
async def test_create_channel_publishes_started_message(setup_redis_subscriber):

    await create_channel(exchange, pair)
    subscriber = setup_redis_subscriber
    # waiting to recive msg
    await asyncio.sleep(1)

    message = await subscriber.get_last_message()
    LOGGER.info(f"Recieved Message: {message}")

    assert message is not None
    assert "started" in message["data"]
