from pydantic import BaseModel, field_validator, Field

from ..enums.exchange import Exchange
from ..enums.market import Market
from ..enums.data_type import DataType
from ..enums.indicator_type import IndicatorType

from typing import List, Dict, Any, Union, Annotated, Literal


# --- Market Subscribe ---
class MarketSubscriptionRequestSchema(BaseModel):
    exchange: Exchange
    market: Market
    data_type: DataType

    @field_validator("data_type")
    def disallow_info(cls, v: DataType):
        if v == DataType.INFO:
            raise ValueError("INFO is not allowed as a data_type")
        return v


# --- Indicator Subscribe ---
class BaseIndicatorRequest(BaseModel):
    exchange: str
    market: str
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


# --- Response Schema ---
class SubscriptionResponseSchema(BaseModel):
    channel: str


class CandleResponseSchema(BaseModel):
    type: str
    response: List[Dict[str, Any]]


class PublishDataSchema(BaseModel):
    data: dict
    type: DataType
