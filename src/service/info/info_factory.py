from ...enums.exchange import Exchange

from .hyperliquid_info import HyperliquidInfo


def get_info(exchange: Exchange):
    if exchange == Exchange.HYPERLIQUID:
        return HyperliquidInfo()
    else:
        raise ValueError(f"There isn't info for {exchange.value}")
