from fifi import RedisBaseModel

from ..enums.exchange import Exchange
from ..enums.market import Market


class SMAModel(RedisBaseModel):
    exchange: Exchange
    market: Market
    sma: float
    slope: float
    time: float
