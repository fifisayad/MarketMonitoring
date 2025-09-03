from ...enums.indicator_type import IndicatorType
from ...enums.exchange import Exchange
from ...enums.market import Market
from .base import BaseIndicator
from .rsi_indicator import RSIIndicator
from .macd_indicator import MACDIndicator
from .sma_indicator import SMAIndicator


def create_indicator(
    exchange: Exchange,
    market: Market,
    data_type: IndicatorType,
    **kwargs,
) -> BaseIndicator:
    if data_type == IndicatorType.RSI:
        return RSIIndicator(exchange=exchange, market=market, **kwargs)
    elif data_type == IndicatorType.MACD:
        return MACDIndicator(exchange=exchange, market=market, **kwargs)
    elif data_type == IndicatorType.SMA:
        return SMAIndicator(exchange=exchange, market=market, **kwargs)
    else:
        raise ValueError(f"There isn't indicator for {data_type.value}")
