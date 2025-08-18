from fifi import RedisBaseModel

from ..enums.exchange import Exchange
from ..enums.market import Market


class MACDModel(RedisBaseModel):
    exchange: Exchange
    market: Market
    macd: float
    signal: float
    histogram: float
    time: float
