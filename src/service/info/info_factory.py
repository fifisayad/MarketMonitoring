from ...enums.exchange import Exchange

from .hyperliquid_info import HyperliquidInfo
from .base import BaseInfo


def get_info(exchange: Exchange) -> BaseInfo:
    if exchange == Exchange.HYPERLIQUID:
        return HyperliquidInfo()
    else:
        raise ValueError(f"There isn't info for {exchange.value}")
