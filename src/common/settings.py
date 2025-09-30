from dotenv import load_dotenv
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HYPERLIQUID_BASE_URL: str = MAINNET_API_URL
    RESTART_TIME_THRESHOLD: float = 10
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "env_nested_delimiter": "__", "extra": "allow"}
