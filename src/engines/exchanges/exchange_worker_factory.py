from .base import BaseExchangeWorker
from .hyperliquid_exchange_worker import HyperliquidExchangeWorker
from .binance_exchange_worker import BinanceExchangeWorker
from fifi.enums import Exchange, Market


def create_exchange_worker(exchange: Exchange, market: Market) -> BaseExchangeWorker:
    if exchange == Exchange.HYPERLIQUID:
        return HyperliquidExchangeWorker(market=market)
    elif exchange == Exchange.BINANCE:
        return BinanceExchangeWorker(market=market)
    else:
        raise ValueError(f"There isn't exchange worker for {exchange}")
