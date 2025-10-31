import json
import time
import threading
import websocket
import numpy as np
from typing import Any, Dict, Literal, Optional

from hyperliquid.info import Info
from hyperliquid.utils import constants

from fifi import log_exception, LoggerFactory, MonitoringSHMRepository
from fifi.enums import Candle, Exchange, Market

from .base import BaseExchangeWorker
from ...common.settings import Settings
from ...helpers.hyperliquid_helpers import *


LOGGER = LoggerFactory().get(__name__)
RECONNECT_MIN_DELAY = 2
RECONNECT_MAX_DELAY = 20


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

        # WS state
        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._ws_stop = False
        self._ws_reset = False
        self.last_update_timestamp = time.time()
        self.reconnect_delay = RECONNECT_MIN_DELAY

        # candle time
        self.current_candle_time = 0
        self.next_candle_time = 0

    @log_exception()
    def start(self):
        self.info = Info(self.base_url, skip_ws=True)
        self._ws_stop = False
        self._ws_thread = threading.Thread(target=self.run_forever, daemon=True)
        self._ws_thread.start()
        LOGGER.info(f"create info and websocket for {self.name}")

    @log_exception()
    def run_forever(self) -> None:
        while not self._ws_stop:
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
                LOGGER.error("Fatal websocket error:", e)

            LOGGER.info(
                f"{self.market.value}: Reconnecting in {self.reconnect_delay}s..."
            )
            time.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, RECONNECT_MAX_DELAY)

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
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
            LOGGER.info(f"{self.market.value}: subscribe trades in ws...")
            self.last_update_timestamp = time.time()
            self.reconnect_delay = RECONNECT_MIN_DELAY
            self._ws_reset = False
        except Exception as e:  # pragma: no cover
            LOGGER.error(str(e))
            raise

    def _on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        try:
            self.last_update_timestamp = time.time()
            self._handle_ws_message(json.loads(message))
        except Exception as e:  # pragma: no cover
            LOGGER.error(str(e))

    def _on_error(
        self, ws: websocket.WebSocketApp, error: Any
    ) -> None:  # pragma: no cover
        LOGGER.error(f"ws: {str(error)}")

    def _send_ws(self, obj: Dict[str, Any]) -> None:
        if not self._ws:
            raise RuntimeError(
                f"{self.market.value}: WebSocket is not started. Call start_ws()."
            )
        self._ws.send(json.dumps(obj))

    def _on_close(
        self, ws: websocket.WebSocketApp, status_code: int, msg: str
    ) -> None:  # pragma: no cover
        self.monitoring_repo.clear_is_updated(self.market)
        LOGGER.error(f"{self.market.value}: closed ws: {status_code=} {msg=}")

    def close_ws(self) -> None:
        try:
            if self._ws:
                self._ws.close()
                self._ws_reset = True
        except:
            pass

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
        price = float(trade["px"])
        size = float(trade["sz"])
        last_candle_time = self.monitoring_repo.get_current_candle_time(self.market)
        self.monitoring_repo.set_last_trade(self.market, float(trade["px"]))
        if trade["time"] - (60 * 1000) > last_candle_time:
            self.init_close_prices(trade["time"])
        if trade["time"] >= self.next_candle_time:
            self.monitoring_repo.candles[self.market_row_index] = np.roll(
                self.monitoring_repo.candles[self.market_row_index],
                shift=-1,
                axis=1,
            )
            self.monitoring_repo.set_current_candle_time(
                self.market, self.next_candle_time
            )
            self.current_candle_time = self.next_candle_time
            self.next_candle_time = self.current_candle_time + (60 * 1000)
            self.monitoring_repo.candles[self.market_row_index, :, -1] = price
            self.monitoring_repo.candles[self.market_row_index][Candle.VOL.value][
                -1
            ] = size
            return
        self.monitoring_repo.candles[self.market_row_index][Candle.CLOSE.value][
            -1
        ] = price
        if (
            price
            < self.monitoring_repo.candles[self.market_row_index][Candle.LOW.value][-1]
        ):
            self.monitoring_repo.candles[self.market_row_index][Candle.LOW.value][
                -1
            ] = price
        if (
            price
            > self.monitoring_repo.candles[self.market_row_index][Candle.HIGH.value][-1]
        ):
            self.monitoring_repo.candles[self.market_row_index][Candle.HIGH.value][
                -1
            ] = price
        self.monitoring_repo.candles[self.market_row_index][Candle.VOL.value] += size

    def init_close_prices(self, trade_time: int):
        trade_time = trade_time - (trade_time % (60 * 1000))
        candles = self.info.candles_snapshot(
            name=market_to_hyper_market(self.market),
            interval="1m",
            startTime=trade_time - (200 * 60 * 1000),
            endTime=trade_time,
        )
        candles_length = len(candles)
        for i in range(self.monitoring_repo.candles_length):
            self.monitoring_repo.candles[self.market_row_index][Candle.CLOSE.value][
                i
            ] = float(
                candles[candles_length - self.monitoring_repo.candles_length + i]["c"]
            )
            self.monitoring_repo.candles[self.market_row_index][Candle.OPEN.value][
                i
            ] = float(
                candles[candles_length - self.monitoring_repo.candles_length + i]["o"]
            )
            self.monitoring_repo.candles[self.market_row_index][Candle.HIGH.value][
                i
            ] = float(
                candles[candles_length - self.monitoring_repo.candles_length + i]["h"]
            )
            self.monitoring_repo.candles[self.market_row_index][Candle.LOW.value][i] = (
                float(
                    candles[candles_length - self.monitoring_repo.candles_length + i][
                        "l"
                    ]
                )
            )
            self.monitoring_repo.candles[self.market_row_index][Candle.VOL.value][i] = (
                float(
                    candles[candles_length - self.monitoring_repo.candles_length + i][
                        "v"
                    ]
                )
            )
        self.current_candle_time = trade_time
        self.next_candle_time = self.current_candle_time + (60 * 1000)
        self.monitoring_repo.set_current_candle_time(
            self.market, self.current_candle_time
        )
        self.monitoring_repo.set_is_updated(self.market)

    @log_exception()
    def reset(self):
        if not self._ws_reset:
            self.close_ws()

    @log_exception()
    def stop(self):
        LOGGER.info(f"shutting down {self.name} exchange worker....")
        self._ws_stop = True
        self.close_ws()
        if self._ws:
            self._ws.keep_running = False
            self._ws = None
        self._ws_thread = None
        self.reconnect_delay = RECONNECT_MIN_DELAY
        LOGGER.info(f"{self.name} exchange worker is closed")
