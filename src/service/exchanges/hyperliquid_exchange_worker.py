import asyncio
import time
import queue
import threading
import random

from hyperliquid.info import Info

from fifi import RedisPublisher, log_exception
from fifi.enums import Exchange, DataType, Market
from fifi.schema import PublishDataSchema
from fifi.helpers.get_logger import LoggerFactory

from .base import BaseExchangeWorker
from ...common.settings import Settings
from ...helpers.hyperliquid_helpers import *


LOGGER = LoggerFactory().get(__name__)


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
        self.last_update_timestamp = 0

    @log_exception()
    async def start(self):
        attempt = 0
        base_delay = 5
        max_delay = 60

        while attempt < 5:
            try:
                self.info = Info(self.base_url)
                break
            except Exception as e:
                attempt += 1
                delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                delay += random.uniform(0, delay / 2)
                LOGGER.error(
                    f"Error creating Info: {e} (attempt {attempt}), retrying in {int(delay)}s..."
                )
                await asyncio.sleep(delay)
        LOGGER.info("create info and websocket to the hyperliquid")
        self.redis_publisher = await RedisPublisher.create(channel=self.channel)
        LOGGER.info(f"create redis_publisher for this {self.channel}...")
        # Start the asyncio loop in a separate thread
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

        # Schedule the redis_publisher coroutine on the loop
        asyncio.run_coroutine_threadsafe(self.publish(), self.loop)
        self.last_update_timestamp = time.time()

    @log_exception()
    async def subscribe(self, data_type: DataType, **kwargs):
        self.message_queue.put(
            PublishDataSchema(
                data={"data": "messages are coming...."}, type=DataType.INFO
            ).model_dump()
        )

        if self.is_data_type_subscribed(data_type, **kwargs):
            return

        LOGGER.info(f"{self.channel} subscribing to {data_type=} {kwargs=}")

        # Build subscription message
        subscription_message = {
            "type": data_type_to_type(data_type),
            "coin": market_to_hyper_market(self.market),
        }

        # Map timeframe -> interval for candles
        if data_type == DataType.CANDLE:
            subscription_message["interval"] = kwargs["timeframe"]

        # Call actual subscription
        self.info.subscribe(
            subscription_message,
            self.message_handler,
        )

        # Track subscription
        self.data_types.add(data_type)
        self.subscriptions.append({"data_type": data_type, **kwargs})

    @log_exception()
    def message_handler(self, msg: dict):
        if "channel" in msg:
            if msg["channel"] == DataType.TRADES:
                msg = PublishDataSchema(
                    data={
                        "price": float(msg["data"][-1]["px"]),
                        "size": float(msg["data"][-1]["sz"]),
                        "time": float(msg["data"][-1]["time"]) / 1000,
                    },
                    type=DataType.TRADES,
                ).model_dump()
            elif msg["channel"] == DataType.CANDLE:
                msg = PublishDataSchema(
                    data=msg["data"],
                    type=DataType.CANDLE,
                    timeframe=msg["data"]["i"],
                ).model_dump()

        self.message_queue.put(msg)
        self.last_update_timestamp = time.time()

    @log_exception()
    async def publish(self):
        while not self._stop_event.is_set():
            message = await self.loop.run_in_executor(None, self.message_queue.get)
            if message:
                await self.redis_publisher.publish(message=message)

    @log_exception()
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
