from pydantic import BaseModel, field_validator, Field, ValidationInfo

from ..enums.exchange import Exchange
from ..enums.market import Market
from ..enums.data_type import DataType
from ..enums.indicator_type import IndicatorType

from typing import List, Dict, Any, Union, Annotated, Literal


# --- Market Subscribe ---
class MarketSubscriptionBase(BaseModel):
    exchange: Exchange
    market: Market
    data_type: DataType


class NonCandleSubscription(MarketSubscriptionBase):
    data_type: Literal[DataType.TRADES, DataType.ORDERBOOK]


class CandleSubscription(MarketSubscriptionBase):
    data_type: Literal[DataType.CANDLE]
    timeframe: Literal["1m", "5m"]


MarketSubscriptionRequestSchema = Annotated[
    Union[CandleSubscription, NonCandleSubscription],
    Field(discriminator="data_type"),
]


# --- Indicator Subscribe ---
class BaseIndicatorRequest(BaseModel):
    exchange: Exchange
    market: Market
    indicator: IndicatorType


# --- RSI specific ---
class RSISubscriptionRequest(BaseIndicatorRequest):
    indicator: Literal[IndicatorType.RSI]
    period: Literal[5, 10, 14] = 14
    timeframe: Literal["1m", "5m"] = "1m"


IndicatorSubscriptionRequest = Annotated[
    Union[RSISubscriptionRequest],
    Field(discriminator="indicator"),
]


# --- Info Schemas ---
class CandleSubscriptionRequestSchema(MarketSubscriptionBase):
    timeframe: Literal["1m", "5m"] = "1m"
    # 🏁 TODO recive period (e.g 500 recent candles) in endpoint

    @field_validator("timeframe")
    def validate_timeframe(cls, v: str, info: ValidationInfo) -> str:
        data_type = info.data.get("data_type")
        if data_type != DataType.CANDLE:
            raise ValueError("timeframe only applies to CANDLE data_type")
        return v


# --- Response Schema ---
class SubscriptionResponseSchema(BaseModel):
    channel: str


class CandleResponseSchema(BaseModel):
    type: str
    response: List[Dict[str, Any]]


class PublishDataSchema(BaseModel):
    data: dict
    type: str = "1m"  # change here too
