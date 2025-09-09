from fifi import RedisBaseModel

from ..enums.exchange import Exchange
from ..enums.market import Market


class RSIModel(RedisBaseModel):
    exchange: Exchange
    market: Market
    timeframe: str
    period: int
    rsi: float
    atr: float = 0.0
    time: float
