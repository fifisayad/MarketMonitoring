import asyncio
import json
import time
import threading
from queue import Queue
from fifi.types.market import intervals_type
import websocket
from typing import Any, Dict, Optional, Set

from hyperliquid.info import Info
from hyperliquid.utils import constants

from fifi import BaseEngine, log_exception, LoggerFactory, MarketDataRepository
from fifi.enums import Exchange, Market

from .base import BaseExchangeWorker
from ...common.settings import Settings
from ...helpers.hyperliquid_helpers import *
from ...helpers.intervals_helpers import *


RECONNECT_MIN_DELAY = 2
RECONNECT_MAX_DELAY = 20


class HyperWS(BaseEngine):
    def __init__(self, market: Market, msg_queue: Queue):
        super().__init__(run_in_process=False)
        self.name = f"HyperWS-{market.value}"
        self.LOGGER = LoggerFactory().get(self.name)
        self.msg_queue = msg_queue
        self.market = market
        self.settings = Settings()

        if self.settings.EXCHANGE_NETWORK == "testnet":
            self.base_url = constants.TESTNET_API_URL
            self.ws_url = "wss://api.hyperliquid-testnet.xyz/ws"
        else:
            self.base_url = constants.MAINNET_API_URL
            self.ws_url = "wss://api.hyperliquid.xyz/ws"

        # WS state
        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._ws_reset = False
        self.last_update_timestamp = time.time()
        self.reconnect_delay = RECONNECT_MIN_DELAY

    async def prepare(self):
        pass

    async def postpare(self):
        pass

    async def execute(self):
        while True:
            try:
                self._ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_open=self._on_open,  # type: ignore
                    on_message=self._on_message,  # type: ignore
                    on_error=self._on_error,  # type: ignore
                    on_close=self._on_close,  # type: ignore
                )
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                self.LOGGER.error("Fatal websocket error:", e)

            self.LOGGER.info(
                f"{self.market.value}: Reconnecting in {self.reconnect_delay}s..."
            )
            time.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, RECONNECT_MAX_DELAY)

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        try:
            self.LOGGER.info(f"opening ws to the {self.name} ...")
            self._send_ws(
                {
                    "method": "subscribe",
                    "subscription": {
                        "type": "trades",
                        key_to_subscribe(self.market): market_to_hyper_market(
                            self.market
                        ),
                    },
                }
            )
            self.LOGGER.info(f"{self.market.value}: subscribe trades in ws...")
            self.last_update_timestamp = time.time()
            self.reconnect_delay = RECONNECT_MIN_DELAY
            self._ws_reset = False
        except Exception as e:  # pragma: no cover
            self.LOGGER.error(str(e))
            raise

    def _on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        try:
            self.last_update_timestamp = time.time()
            self._handle_ws_message(json.loads(message))
        except Exception as e:  # pragma: no cover
            self.LOGGER.error(str(e))

    def _on_error(
        self, ws: websocket.WebSocketApp, error: Any
    ) -> None:  # pragma: no cover
        self.LOGGER.error(f"ws: {str(error)}")

    def _send_ws(self, obj: Dict[str, Any]) -> None:
        if not self._ws:
            raise RuntimeError(
                f"{self.market.value}: WebSocket is not started. Call start_ws()."
            )
        self._ws.send(json.dumps(obj))

    def _on_close(
        self, ws: websocket.WebSocketApp, status_code: int, msg: str
    ) -> None:  # pragma: no cover
        self._ws_reset = True
        self.LOGGER.error(f"{self.market.value}: closed ws: {status_code=} {msg=}")

    def close_ws(self) -> None:
        try:
            if self._ws:
                self._ws.close()
                self._ws_reset = True
        except:
            pass

    def reset(self):
        if not self._ws_reset:
            self.close_ws()

    @log_exception()
    def _handle_ws_message(self, msg: Dict[str, Any]) -> None:
        channel = msg.get("channel")
        data = msg.get("data")
        if channel == "subscriptionResponse":
            return
        if channel == "trades":
            if isinstance(data, list):
                self.msg_queue.put(data)

        self.last_update_timestamp = time.time()


class TradesInterpretor(BaseEngine):
    _repos: Dict[intervals_type, MarketDataRepository]
    _unique_traders: Dict[intervals_type, Set[str]]
    info: Info

    def __init__(self, market: Market, msg_queue: Queue):
        super().__init__(run_in_process=False)
        self.name = f"TradesInterpretor-{market.value}"
        self.LOGGER = LoggerFactory().get(self.name)
        self.msg_queue = msg_queue
        self.market = market
        self.settings = Settings()
        self.intervals = self.settings.INTERVALS
        self.info = Info(skip_ws=True)

    @log_exception()
    async def prepare(self):
        for interval in self.intervals:
            self._repos[interval] = MarketDataRepository(
                market=self.market, interval=interval, create=True
            )
            self._unique_traders[interval] = set()
            self.update_data(last_trade_time=0, interval=interval)
            await asyncio.sleep(60)

    @log_exception()
    async def execute(self):
        while True:
            trades = self.msg_queue.get()
            for trade in trades:
                for interval in self.intervals:
                    self._ingest_trade(trade=trade, interval=interval)

    def _ingest_trade(self, trade: Dict, interval: intervals_type):
        price = float(trade["px"])
        size = float(trade["sz"])
        last_candle_time = self._repos[interval].get_time()
        next_candle_time = last_candle_time + to_time(interval)
        if trade["time"] < last_candle_time:
            # not consider this trade
            return
        elif trade["time"] - to_time(interval) > last_candle_time:
            self.update_data(last_trade_time=trade["time"], interval=interval)
            return
        elif trade["time"] >= next_candle_time:
            self._repos[interval].create_candle()
            self._unique_traders[interval].clear()
            self._repos[interval].set_time(next_candle_time)
            self._repos[interval].set_open_price(price)
        self._repos[interval].set_last_trade(price)
        self._repos[interval].add_vol(size)
        self._repos[interval].set_close_price(price)
        if price < self._repos[interval].get_lows(-1)[0]:
            self._repos[interval].set_low_price(price)
        if price > self._repos[interval].get_highs(-1)[0]:
            self._repos[interval].set_high_price(price)

        if trade["side"] == "B":
            self._repos[interval].add_buyer_vol(size)
        else:
            self._repos[interval].add_seller_vol(size)

        for user in trade["users"]:
            if not user in self._unique_traders[interval]:
                self._unique_traders[interval].add(user)
                self._repos[interval].add_unique_traders(1)

    def update_data(self, last_trade_time: int, interval: intervals_type) -> None:
        end_time = last_trade_time - (last_trade_time % to_time(interval))
        if last_trade_time == 0:
            start_time = end_time - (self._repos[interval]._rows * to_time(interval))
        else:
            start_time = int(self._repos[interval].get_time())
        candles = self.info.candles_snapshot(
            name=market_to_hyper_market(self.market),
            interval=interval,
            endTime=end_time,
            startTime=start_time,
        )
        for candle in candles:
            if candle["t"] == end_time:
                continue
            self._repos[interval].create_candle()
            self._repos[interval].set_last_trade(float(candle["c"]))
            self._repos[interval].set_close_price(float(candle["c"]))
            self._repos[interval].set_open_price(float(candle["o"]))
            self._repos[interval].set_high_price(float(candle["h"]))
            self._repos[interval].set_low_price(float(candle["l"]))
            self._repos[interval].set_vol(float(candle["v"]))
            self._repos[interval].set_time(candle["t"])

    def raise_unhealthy(self):
        for interval in self.intervals:
            self._repos[interval].health.clear_is_updated()

    def back_to_healthy(self):
        for interval in self.intervals:
            self._repos[interval].health.set_is_updated()

    async def postpare(self):
        for interval, repo in self._repos.items():
            repo.close()


class HyperliquidExchangeWorker(BaseExchangeWorker):
    exchange = Exchange.HYPERLIQUID
    base_url: str
    ws_url: str
    name: str

    def __init__(
        self,
        market: Market,
    ):
        super().__init__(market)
        self.name = f"{self.exchange.value}_{self.market.value}"
        self.LOGGER = LoggerFactory().get(self.name)
        self.settings = Settings()

    @log_exception()
    def ignite(self):
        self.start()

    @log_exception()
    async def prepare(self):
        self.LOGGER.info("init worker exchange...")
        self.msg_queue = Queue()
        self.hyper_ws = HyperWS(market=self.market, msg_queue=self.msg_queue)
        self.hyper_ws.start()
        self.trades_intrepretor = TradesInterpretor(
            market=self.market, msg_queue=self.msg_queue
        )
        self.trades_intrepretor.start()
        self.hard_reset = False
        self.soft_reset = False

    @log_exception()
    async def execute(self):
        # watch dog procedure
        while True:
            if (
                time.time() - self.hyper_ws.last_update_timestamp
                > self.settings.HARD_RESET_TIME_THRESHOLD
            ):
                if self.hard_reset:
                    raise Exception("Hard Reset Not Working")
                try:
                    self.trades_intrepretor.raise_unhealthy()
                    self.LOGGER.critical(f"HARD reset")
                    self.hyper_ws.stop()
                    del self.hyper_ws
                    self.hyper_ws = HyperWS(
                        market=self.market, msg_queue=self.msg_queue
                    )
                    self.hyper_ws.start()
                    self.hard_reset = True
                except Exception as e:
                    self.LOGGER.error(f"Error: {e}")

            elif (
                time.time() - self.hyper_ws.last_update_timestamp
                > self.settings.RESET_TIME_THRESHOLD
            ):
                self.trades_intrepretor.raise_unhealthy()
                self.LOGGER.info(f"SOFT reset")
                self.hyper_ws.reset()
                self.soft_reset = True
            elif self.hard_reset or self.soft_reset:
                self.trades_intrepretor.back_to_healthy()
                self.hard_reset = False
                self.soft_reset = False
            await asyncio.sleep(10)

    async def postpare(self):
        return await super().postpare()

    @log_exception()
    def shutdown(self):
        self.LOGGER.info(f"shutting down {self.name} exchange worker....")
        self.trades_intrepretor.stop()
        self.hyper_ws.stop()
        self.stop()
        self.LOGGER.info(f"{self.name} exchange worker is closed")
