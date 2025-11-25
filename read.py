import argparse
from typing import Dict, List, Optional
from fifi.enums import Market
from fifi.enums.market import MarketStat
from fifi import MarketStatRepository, MarketDataRepository, LoggerFactory
from fifi.types.market import intervals_type

from src.common.settings import Settings


settings = Settings()
LOGGER = LoggerFactory().get(__name__)


def get_market_last_candle(repo: MarketDataRepository) -> List[str | float]:
    close = repo.get_closes()[-1]
    open = repo.get_opens()[-1]
    high = repo.get_highs()[-1]
    low = repo.get_lows()[-1]
    vol = round(repo.get_vols()[-1], 2)
    svol = round(repo.get_seller_vol(), 2)
    bvol = round(repo.get_buyer_vol(), 2)
    traders = round(repo.get_unique_traders(), 2)
    alive = "\u2705" if repo.health.is_updated() else "\U0001f6d1"

    return [alive, close, open, high, low, vol, svol, bvol, traders]


def get_market_last_stat(repo: MarketStatRepository) -> List[float]:
    rsi = repo.get_last_stat(MarketStat.RSI14)
    atr = repo.get_last_stat(MarketStat.ATR14)
    hma = repo.get_last_stat(MarketStat.HMA)
    return [rsi, atr, hma]


def read_shm(
    market: Optional[Market],
    stat: Optional[MarketStat],
    interval: Optional[intervals_type],
) -> None:
    stat_repos: Dict[Market, Dict[intervals_type, MarketStatRepository]] = dict()
    data_repos: Dict[Market, Dict[intervals_type, MarketDataRepository]] = dict()
    if interval is not None:
        intervals: List[intervals_type] = [interval]
    else:
        intervals = settings.INTERVALS
    for interv in intervals:
        if market:
            if market not in stat_repos:
                stat_repos[market] = dict()
            if market not in data_repos:
                data_repos[market] = dict()
            stat_repos[market][interv] = MarketStatRepository(
                interval=interv, market=market
            )
            data_repos[market][interv] = MarketDataRepository(
                interval=interv, market=market
            )
        else:
            for market in settings.MARKETS:
                if market not in stat_repos:
                    stat_repos[market] = dict()
                if market not in data_repos:
                    data_repos[market] = dict()
                stat_repos[market][interv] = MarketStatRepository(
                    interval=interv, market=market
                )
                data_repos[market][interv] = MarketDataRepository(
                    interval=interv, market=market
                )

    if stat:
        for market, interval_repo in stat_repos.items():
            for interv, repo in interval_repo.items():
                stat_value = repo.get_last_stat(stat=stat)
                LOGGER.info(f"{market.value.upper()}-> {stat.value}={stat_value}")
        return

    print("\n######################################################################\n")
    # candles data
    print("CANDLES")
    candles_data: List[List[str | float]] = [
        [
            "market",
            "interval",
            "alive",
            "close",
            "open",
            "high",
            "low",
            "vol",
            "svol",
            "bvol",
            "traders",
        ]
    ]
    for market, interval_repo in data_repos.items():
        for interv, repo in interval_repo.items():
            data = [market.value, interv]
            candle = get_market_last_candle(repo)
            candles_data.append(data + candle)
    widths = [
        max(len(str(row[i])) for row in candles_data)
        for i in range(len(candles_data[0]))
    ]
    for row in candles_data:
        print(" | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))

    print("\n######################################################################\n")
    # stats data
    print("STATS")
    stat_data: List[List[str | float]] = [
        [
            "market",
            "interval",
            "rsi",
            "atr",
            "hma",
        ]
    ]
    for market, interval_repo in stat_repos.items():
        for interv, repo in interval_repo.items():
            data = [market.value, interv]
            stats = get_market_last_stat(repo)
            stat_data.append(data + stats)
    widths = [
        max(len(str(row[i])) for row in stat_data) for i in range(len(stat_data[0]))
    ]
    for row in stat_data:
        print(" | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))

    print("\n######################################################################\n")


def main():
    parser = argparse.ArgumentParser(description="Shared Memory Key/Value CLI")

    parser.add_argument(
        "--market", type=str, default=None, required=False, help="Read Market"
    )
    parser.add_argument(
        "--stat", type=str, default=None, required=False, help="Read Market Stat"
    )
    parser.add_argument(
        "--interval", type=str, default=None, required=False, help="Read Interval"
    )
    args = parser.parse_args()

    market = None
    market_stat = None
    interval = None
    if args.market:
        market = Market(args.market)
        if market not in settings.MARKETS:
            raise ValueError(f"this {args.market=} is not in configuration")
    if args.stat:
        market_stat = MarketStat[args.stat]
    if args.interval:
        interval = args.interval
        if interval not in settings.INTERVALS:
            raise ValueError(f"this {interval=} not in the settings")
    LOGGER.info(f"connected to the SHM")
    read_shm(market, market_stat, interval)


if __name__ == "__main__":
    main()
