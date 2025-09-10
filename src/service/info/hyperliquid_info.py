import time
from typing import Any, Dict, List

from fifi import singleton
from hyperliquid.info import Info

from .base import BaseInfo
from ...common.settings import Settings
from ...helpers.hyperliquid_helpers import market_to_hyper_market
from ...enums.market import Market


@singleton
class HyperliquidInfo(BaseInfo):
    last_candles: List[Dict[Any, Any]]

    def __init__(self) -> None:
        self.settings = Settings()
        self.info = Info(self.settings.HYPERLIQUID_BASE_URL, skip_ws=True)
        self.last_candles = []

    def candle_snapshot(
        self,
        market: Market,
        timeframe: str = "1m",
        period: int = 500,
    ) -> List[Dict[Any, Any]]:
        """
        Get historical candle snapshot.

        Args:
            market (Market): Target market.
            interval (str, optional): Candle timeframe (e.g., "1m", "5m", "1h"). Defaults to "1m".
            period (int, optional): Number of recent candles to fetch. Defaults to 500.

        Returns:
            List[dict]: List of candle data points.
        """
        # 🏁 TODO add timeframe to period for actual results
        now_ms = int(time.time() / 60) * 60 * 1000
        start_time = now_ms - (period * 60 * 1000)

        if self.last_candles and int(self.last_candles[-1]["t"]) == now_ms:
            return self.last_candles

        candles = self.info.candles_snapshot(
            name=market_to_hyper_market(market),
            interval=timeframe,
            startTime=start_time,
            endTime=now_ms,
        )
        self.last_candles = candles
        return candles
