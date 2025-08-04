import asyncio
import queue
import threading
from hyperliquid.info import Info
from fifi import GetLogger, RedisPublisher

from ...common.schemas import PublishDataSchema
from .base import BaseExchangeWorker
from ...enums.exchange import Exchange
from ...enums.market import Market
from ...enums.data_type import DataType
from ...common.settings import Settings


def data_type_to_type(
    data_type: DataType,
) -> str:
    if data_type == DataType.TRADES:
        return "trades"
    elif data_type == DataType.ORDERBOOK:
        return "l2Book"
    else:
        raise ValueError(f"there is no data type fo {data_type.value} in hyperliquid")


def market_to_hyper_market(market: Market) -> str:
    if market == Market.BTCUSD:
        return "BTC/USDC"
    elif market == Market.BTCUSD_PERP:
        return "BTC"
    else:
        raise ValueError(f"There is no market={market.value} in hyperliquid")


LOGGER = GetLogger().get()


class HyperliquidExchangeWorker(BaseExchangeWorker):
    exchange = Exchange.HYPERLIQUID
    base_url: str
    info: Info

    def __init__(self, market: Market):
        super().__init__(market)
        self.settings = Settings()
        self.base_url = self.settings.HYPERLIQUID_BASE_URL
        self.message_queue = queue.Queue()
        self.loop = asyncio.new_event_loop()
        self._stop_event = threading.Event()

    async def start(self):
        self.info = Info(self.base_url)
        LOGGER.info("create info and websocket to the hyperliquid")
        self.redis_publisher = await RedisPublisher.create(channel=self.channel)
        LOGGER.info(f"create redis_publisher for this {self.channel}...")
        # Start the asyncio loop in a separate thread
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

        # Schedule the redis_publisher coroutine on the loop
        asyncio.run_coroutine_threadsafe(self.publish(), self.loop)

    async def subscribe(self, data_type: DataType):
        self.message_queue.put(
            PublishDataSchema(
                data={"data": "messages are coming...."}, type=DataType.INFO
            ).model_dump()
        )
        if self.is_data_type_subscribed(data_type):
            return
        LOGGER.info(f"this {self.channel} worker exchange subscribe this {data_type=}")
        self.info.subscribe(
            {  # type: ignore
                "type": data_type_to_type(data_type),
                "coin": market_to_hyper_market(self.market),
            },
            self.message_handler,
        )
        self.data_types.add(data_type)

    def message_handler(self, msg: dict):
        if "channel" in msg:
            if msg["channel"] == "trades":
                msg = PublishDataSchema(
                    data={
                        "price": msg["data"][-1]["px"],
                        "size": msg["data"][-1]["sz"],
                    },
                    type=DataType.TRADES,
                ).model_dump()

        self.message_queue.put(msg)

    async def publish(self):
        while not self._stop_event.is_set():
            message = await self.loop.run_in_executor(None, self.message_queue.get)
            if message:
                await self.redis_publisher.publish(message=message)

    async def stop(self):
        LOGGER.info(f"shutting down {self.channel} work exchange....")
        self._stop_event.set()
        if self.__dict__.get("info", None):
            self.info.disconnect_websocket()
        asyncio.run_coroutine_threadsafe(
            self.redis_publisher.redis_client.close(), self.loop
        )

        # Stop event loop
        def shutdown_loop():
            self.loop.stop()

        self.loop.call_soon_threadsafe(shutdown_loop)
        self.thread.join()
        LOGGER.info(f"{self.channel} work exchange is closed")
