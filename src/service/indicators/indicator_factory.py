from ...enums.indicator_type import IndicatorType
from ...enums.exchange import Exchange
from ...enums.market import Market
from .base import BaseIndicator
from .rsi.hyperliquid_rsi_indicator import HyperLiquidRSIIndicator
from .macd_indicator import MACDIndicator
from .sma_indicator import SMAIndicator


def create_indicator_worker(
    exchange: Exchange,
    market: Market,
    data_type: IndicatorType,
    **kwargs,
) -> BaseIndicator:
    if data_type == IndicatorType.RSI:
        if exchange == Exchange.HYPERLIQUID:
            return HyperLiquidRSIIndicator(exchange=exchange, market=market)
    elif data_type == IndicatorType.MACD:
        return MACDIndicator(exchange=exchange, market=market)
    elif data_type == IndicatorType.SMA:
        return SMAIndicator(exchange=exchange, market=market)
    raise ValueError(f"couldnt find {data_type.value} indicator for {exchange.value}")
