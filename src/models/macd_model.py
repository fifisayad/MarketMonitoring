from fifi import RedisBaseModel
from fifi.enums import Exchange, Market


class MACDModel(RedisBaseModel):
    exchange: Exchange
    market: Market
    macd: float
    signal: float
    histogram: float
    time: float
