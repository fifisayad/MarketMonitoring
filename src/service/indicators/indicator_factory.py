from ...enums.data_type import DataType
from ...enums.exchange import Exchange
from ...enums.market import Market
from .base import BaseIndicator
from .rsi_indicator import RSIIndicator
from .macd_indicator import MACDIndicator
from .sma_indicator import SMAIndicator


def create_indicator(
    exchange: Exchange, market: Market, data_type: DataType
) -> BaseIndicator:
    if data_type == DataType.RSI:
        return RSIIndicator(exchange=exchange, market=market)
    elif data_type == DataType.MACD:
        return MACDIndicator(exchange=exchange, market=market)
    elif data_type == DataType.SMA:
        return SMAIndicator(exchange=exchange, market=market)
    else:
        raise ValueError(f"There isn't indicator for {data_type.value}")
