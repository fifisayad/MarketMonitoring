from fifi import RedisBaseModel
from fifi.enums import Exchange, Market


class SMAModel(RedisBaseModel):
    exchange: Exchange
    market: Market
    sma: float
    slope: float
    time: float
