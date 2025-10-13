from typing import Annotated, List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, NoDecode
from pydantic import field_validator
from fifi.enums import Exchange, Market


class Settings(BaseSettings):
    def __init__(self):
        load_dotenv()
        super().__init__()

    EXCHANGES: Annotated[Exchange, NoDecode] = Exchange.HYPERLIQUID

    @field_validator("EXCHANGES", mode="before")
    @classmethod
    def decode_exchanges(cls, v: str) -> Exchange:
        return Exchange(v)

    MARKETS: Annotated[List[Market], NoDecode] = [Market.BTCUSD_PERP]

    @field_validator("MARKETS", mode="before")
    @classmethod
    def decode_markets(cls, v: str) -> list[Market]:
        return [Market(x) for x in v.split(",")]

    RESTART_TIME_THRESHOLD: float = 10
    LOG_LEVEL: str = "INFO"
    model_config = {"env_file": ".env", "env_nested_delimiter": "__", "extra": "allow"}
