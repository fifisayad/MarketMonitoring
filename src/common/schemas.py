from pydantic import BaseModel, field_validator

from ..enums.exchange import Exchange
from ..enums.market import Market
from ..enums.data_type import DataType
from ..enums.indicator_type import IndicatorType

from typing import List, Dict, Any


class MarketSubscriptionRequestSchema(BaseModel):
    exchange: Exchange
    market: Market
    data_type: DataType

    @field_validator("data_type")
    def disallow_info(cls, v: DataType):
        if v == DataType.INFO:
            raise ValueError("INFO is not allowed as a data_type")
        return v


class IndicatorSubscriptionRequest(BaseModel):
    exchange: str
    market: str
    indicator: IndicatorType


class SubscriptionResponseSchema(BaseModel):
    channel: str


class CandleResponseSchema(BaseModel):
    type: str
    response: List[Dict[str, Any]]


class PublishDataSchema(BaseModel):
    data: dict
    type: DataType
