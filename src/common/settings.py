from dotenv import load_dotenv
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    def __init__(self):
        load_dotenv()
        super().__init__()

    HYPERLIQUID_BASE_URL: str = MAINNET_API_URL
    RESTART_TIME_THRESHOLD: float = 10
    LOG_LEVEL: str = "INFO"
