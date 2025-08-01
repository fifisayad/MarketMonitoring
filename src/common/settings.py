from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HYPERLIQUID_BASE_URL: str = MAINNET_API_URL
