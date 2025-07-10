from pydantic import BaseModel
from src.common.enums import ExchangeEnum, PairEnum


class SubscriptionRequest(BaseModel):
    """
    SubscriptionRequest represents the payload required to subscribe
    to market data for a specific trading pair on a given exchange.

    Attributes:
    ----------
    exchange : ExchangeEnum
        The target cryptocurrency exchange (e.g., Binance, Coinbase).
        Enum ensures only supported exchanges are accepted.

    pair : str
        The trading pair to subscribe to (e.g., "BTC/USDT").
    """

    exchange: ExchangeEnum
    pair: PairEnum
