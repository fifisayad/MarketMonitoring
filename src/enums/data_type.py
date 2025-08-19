from enum import Enum


class DataType(Enum):
    INFO = "info"

    # Market Data
    TRADES = "trades"
    ORDERBOOK = "orderbook"

    # indicators
    RSI = "rsi"
    MACD = "macd"
