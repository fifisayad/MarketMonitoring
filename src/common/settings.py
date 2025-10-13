from typing import List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import field_validator
from fifi.enums import Exchange, Market


class Settings(BaseSettings):
    def __init__(self):
        load_dotenv()
        super().__init__()

    EXCHANGES: List[Exchange] = [Exchange.HYPERLIQUID]

    @field_validator("EXCHANGES", mode="before")
    @classmethod
    def decode_exchanges(cls, v: str) -> List[Exchange]:
        return [Exchange(x) for x in v.split(",")]

    MARKETS: List[Market] = [Market.BTCUSD_PERP]

    @field_validator("MARKETS", mode="before")
    @classmethod
    def decode_markets(cls, v: str) -> list[Market]:
        return [Market(x) for x in v.split(",")]

    RESTART_TIME_THRESHOLD: float = 10
    LOG_LEVEL: str = "INFO"
