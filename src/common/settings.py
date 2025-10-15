from typing import Annotated, List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, NoDecode
from pydantic import field_validator
from fifi.enums import Exchange, Market


class Settings(BaseSettings):
    def __init__(self):
        load_dotenv()
        super().__init__()

    EXCHANGE: Annotated[Exchange, NoDecode] = Exchange.HYPERLIQUID

    @field_validator("EXCHANGE", mode="before")
    @classmethod
    def decode_exchanges(cls, v: str) -> Exchange:
        return Exchange(v)

    MARKETS: Annotated[List[Market], NoDecode] = [Market.BTCUSD_PERP]

    @field_validator("MARKETS", mode="before")
    @classmethod
    def decode_markets(cls, v: str) -> list[Market]:
        return [Market(x) for x in v.split(",")]

    INDICATORS_PERIODS: Annotated[list[int], NoDecode] = [5, 7, 14]

    @field_validator("INDICATORS_PERIODS", mode="before")
    @classmethod
    def decode_indicator_periods(cls, v: str) -> list[int]:
        return [int(x) for x in v.split(",")]

    RESTART_TIME_THRESHOLD: float = 10
    LOG_LEVEL: str = "INFO"
