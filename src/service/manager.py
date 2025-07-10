from src.common.schemas import SubscriptionRequest
from src.common.enums import ExchangeEnum, PairEnum

from src.service.exchanges import hyper

from fifi.redis.redis_client import RedisClient
from fifi.redis.redis_publisher import RedisPublisher


async def handle_subscription(request: SubscriptionRequest):
    # TODO -> asyncio.gather?? for ensuring that both of these works togther?
    await start_exchange_service(request.exchange, request.pair),
    await create_channel(request.exchange, request.pair),


async def start_exchange_service(exchange: str, pair: str):
    if exchange in ExchangeEnum and pair in PairEnum:
        print(ExchangeEnum.hyper.name)
        # await EXCHANGE_MAP[exchange].run(pair)
        return {exchange: pair}
    else:
        raise ValueError("Unsupported exchange")


async def create_channel(exchange: str, pair: str):
    redis_client = await RedisClient.create()
    redispub = RedisPublisher(redis_client, exchange + "-" + pair)
    await redispub.publish({"data": "started"})


async def handle_unsubscription(request: SubscriptionRequest):
    pass
