from enum import Enum


class DataType(str, Enum):
    INFO = "info"

    # Market Data
    TRADES = "trades"
    ORDERBOOK = "orderbook"
    CANDLE = "candle"
