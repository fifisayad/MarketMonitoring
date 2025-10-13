import json
import time
import threading
import websocket
import numpy as np
from typing import Any, Dict, Literal, Optional

from hyperliquid.info import Info
from hyperliquid.utils import constants

from fifi import log_exception, LoggerFactory, MonitoringSHMRepository
from fifi.enums import Exchange, Market

from .base import BaseExchangeWorker
from ...common.settings import Settings
from ...helpers.hyperliquid_helpers import *


LOGGER = LoggerFactory().get(__name__)


class HyperliquidExchangeWorker(BaseExchangeWorker):
    exchange = Exchange.HYPERLIQUID
    base_url: str
    ws_url: str
    name: str
    info: Info

    def __init__(
        self,
        market: Market,
        monitoring_repo: MonitoringSHMRepository,
        network: Literal["mainnet", "testnet"] = "mainnet",
    ):
        super().__init__(market, monitoring_repo)
        self.name = f"{self.exchange.value}_{self.market.value}"
        self.market_row_index = self.monitoring_repo.row_index[self.market]
        self.settings = Settings()

        if network == "testnet":
            self.base_url = constants.TESTNET_API_URL
            self.ws_url = "wss://api.hyperliquid-testnet.xyz/ws"
        else:
            self.base_url = constants.MAINNET_API_URL
            self.ws_url = "wss://api.hyperliquid.xyz/ws"

        self.last_update_timestamp = 0

        # WS state
        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._ws_stop = threading.Event()

        # candle time
        self.current_candle_time = 0
        self.next_candle_time = 0

    @log_exception()
    def start(self):
        self.info = Info(self.base_url, skip_ws=True)
        self.start_ws()
        LOGGER.info(f"create info and websocket for {self.name}")

    @log_exception()
    def start_ws(
        self,
    ) -> None:
        """Start the websocket and subscribe to user channels.

        Stores `orderUpdates` and `userFills` keyed by `oid`.
        """

        if self._ws_thread and self._ws_thread.is_alive():
            return

        def _on_open(_: websocket.WebSocketApp) -> None:
            try:
                LOGGER.info(f"opening ws to the {self.name} ...")
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
                LOGGER.info(f"subscribe trades in ws...")
            except Exception as e:  # pragma: no cover
                LOGGER.error(str(e))
                raise

        def _on_message(_: websocket.WebSocketApp, message: str) -> None:
            try:
                self._handle_ws_message(json.loads(message))
            except Exception as e:  # pragma: no cover
                LOGGER.error(str(e))

        def _on_error(
            _: websocket.WebSocketApp, error: Any
        ) -> None:  # pragma: no cover
            LOGGER.error(f"ws: {str(error)}")

        def _on_close(
            _: websocket.WebSocketApp, status_code: int, msg: str
        ) -> None:  # pragma: no cover
            self.monitoring_repo.clear_is_updated(self.market)
            # Auto-reconnect loop
            if not self._ws_stop.is_set():
                time.sleep(1.0)
                self._spawn_ws()

        self._ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=_on_open,  # type: ignore
            on_message=_on_message,  # type: ignore
            on_error=_on_error,  # type: ignore
            on_close=_on_close,  # type: ignore
        )
        self._ws_stop.clear()
        self._ws_thread = threading.Thread(
            target=self._run_ws_forever, name="HL-WS", daemon=True
        )
        self._ws_thread.start()

    def stop_ws(self) -> None:
        self._ws_stop.set()
        try:
            if self._ws:
                self._ws.close()
        finally:
            self._ws = None
            self._ws_thread = None

    def _spawn_ws(self) -> None:
        # internal reconnect helper
        t = threading.Thread(target=self._run_ws_forever, name="HL-WS", daemon=True)
        self._ws_thread = t
        t.start()

    def _run_ws_forever(self) -> None:
        assert self._ws is not None
        # Enable built-in ping/pong to keep the connection alive
        self._ws.run_forever(ping_interval=20, ping_timeout=10)

    def _send_ws(self, obj: Dict[str, Any]) -> None:
        if not self._ws:
            raise RuntimeError("WebSocket is not started. Call start_ws().")
        self._ws.send(json.dumps(obj))

    @log_exception()
    def _handle_ws_message(self, msg: Dict[str, Any]) -> None:
        channel = msg.get("channel")
        data = msg.get("data")
        if channel == "subscriptionResponse":
            return
        if channel == "trades":
            if isinstance(data, list):
                for trade in data:
                    self._ingest_trade(trade)

        self.last_update_timestamp = time.time()

    def _ingest_trade(self, trade: dict):
        last_candle_time = self.monitoring_repo.get_current_candle(self.market)
        self.monitoring_repo.set_last_trade(self.market, float(trade["px"]))
        if trade["time"] - (60 * 1000) > last_candle_time:
            self.init_close_prices(trade["time"])
        if trade["time"] >= self.next_candle_time:
            self.monitoring_repo.close_prices[self.market_row_index] = np.roll(
                self.monitoring_repo.close_prices[self.market_row_index], -1
            )
            self.monitoring_repo.set_current_candle(self.market, self.next_candle_time)
            self.current_candle_time = self.next_candle_time
            self.next_candle_time = self.current_candle_time + (60 * 1000)
            self.monitoring_repo.set_current_candle(
                self.market, self.current_candle_time
            )
        self.monitoring_repo.close_prices[self.market_row_index][-1] = float(
            float(trade["px"])
        )

    def init_close_prices(self, trade_time: int):
        trade_time = trade_time - (trade_time % (60 * 1000))
        candles = self.info.candles_snapshot(
            name=market_to_hyper_market(self.market),
            interval="1m",
            startTime=trade_time - (200 * 60 * 1000),
            endTime=trade_time,
        )
        candles_length = len(candles)
        for i in range(self.monitoring_repo.close_prices_length):
            self.monitoring_repo.close_prices[self.market_row_index][i] = float(
                candles[candles_length - self.monitoring_repo.close_prices_length + i][
                    "c"
                ]
            )
        self.current_candle_time = trade_time
        self.next_candle_time = self.current_candle_time + (60 * 1000)
        self.monitoring_repo.set_current_candle(self.market, self.current_candle_time)
        self.monitoring_repo.set_is_updated(self.market)

    @log_exception()
    def stop(self):
        LOGGER.info(f"shutting down {self.name} exchange worker....")
        self.stop_ws()
        LOGGER.info(f"{self.name} exchange worker is closed")
