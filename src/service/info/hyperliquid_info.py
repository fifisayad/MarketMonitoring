from hyperliquid.info import Info
from ...common.settings import Settings
import time
from ...helpers.hyperliquid_helpers import market_to_hyper_market
from ...enums.market import Market
from ...enums.data_type import DataType


def candle_snapshot(market: Market, interval=DataType.CANDLE1M, count=200):
    """getting candle snapshot as htorical data

    Args:
        market (Market): Name of the targeted market
        interval (_type_, optional): timeframes 1m, 10m, ... Defaults to DataType.CANDLE1M.
        count (int, optional): number of reent candles. Defaults to 200.

    Returns:
        _type_: candle data
    """
    settings = Settings()
    info = Info(settings.HYPERLIQUID_BASE_URL, skip_ws=True)
    now_ms = int(time.time() * 1000)
    minutes_ago_ms = now_ms - (count * 60 * 1000)
    candles = info.candles_snapshot(
        name=market_to_hyper_market(market),
        interval=interval.split("candle")[1],
        startTime=minutes_ago_ms,
        endTime=now_ms,
    )
    return candles
