from fifi import RedisBaseModel

from ..enums.exchange import Exchange
from ..enums.market import Market


class RSIModel(RedisBaseModel):
    exchange: Exchange
    market: Market
    rsi: float
    time: float
