from pydantic import BaseModel

from ..enums.exchange import Exchange
from ..enums.market import Market
from ..enums.data_type import DataType


class SubscriptionRequestSchema(BaseModel):
    exchange: Exchange
    market: Market
    data_type: DataType


class SubscriptionResponseSchema(BaseModel):
    channel: str


class PublishDataSchema(BaseModel):
    data: dict
    type: DataType
