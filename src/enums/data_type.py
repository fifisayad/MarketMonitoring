from enum import Enum


class DataType(Enum):
    INFO = "info"

    # Market Data
    TRADES = "trades"
    ORDERBOOK = "orderbook"
    CANDLE1M = "candle1m"
