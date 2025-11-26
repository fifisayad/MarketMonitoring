from typing import Annotated, List, Literal
from dotenv import load_dotenv
from fifi.types.market import intervals_type
from pydantic_settings import BaseSettings, NoDecode
from pydantic import field_validator
from fifi.enums import Exchange, Market


class Settings(BaseSettings):
    def __init__(self):
        load_dotenv()
        super().__init__()

    EXCHANGE_NETWORK: Literal["main", "test"] = "main"
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

    INTERVALS: Annotated[list[intervals_type], NoDecode] = [
        "1m",
        "5m",
        "30m",
        "1h",
        "1d",
        "1w",
    ]

    @field_validator("INTERVALS", mode="before")
    @classmethod
    def decode_intervals(cls, v: str) -> list[str]:
        return [x for x in v.split(",")]

    RESET_TIME_THRESHOLD: float = 20
    HARD_RESET_TIME_THRESHOLD: float = 30
    LOG_LEVEL: str = "INFO"
