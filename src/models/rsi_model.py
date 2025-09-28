from fifi import RedisBaseModel
from fifi.enums import Market, Exchange


class RSIModel(RedisBaseModel):
    exchange: Exchange
    market: Market
    timeframe: str
    period: int
    rsi: float
    atr: float = 0.0
    time: float
