from pydantic import BaseModel

from ..enums.exchange import Exchange
from ..enums.market import Market


class SubscriptionRequestSchema(BaseModel):
    exchange: Exchange
    market: Market
