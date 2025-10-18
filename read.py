import argparse
from typing import List, Optional
from fifi.enums import Market, MarketStat
from fifi import MonitoringSHMRepository, LoggerFactory

from src.common.settings import Settings


settings = Settings()
LOGGER = LoggerFactory().get(__name__)


def get_market_last_candle(
    repo: MonitoringSHMRepository, market: Market
) -> List[float]:
    close = repo.get_close_prices(market)[-1]
    open = repo.get_open_prices(market)[-1]
    high = repo.get_high_prices(market)[-1]
    low = repo.get_low_prices(market)[-1]
    vol = repo.get_vols(market)[-1]
    return [close, open, high, low, vol]


def read_shm(
    repo: MonitoringSHMRepository, market: Optional[Market], stat: Optional[MarketStat]
) -> None:
    if stat:
        if market:
            stat_value = repo.get_stat(market, stat)
            LOGGER.info(f"{market.value.upper()}-> {stat.value}={stat_value}")
        else:
            for market_con in settings.MARKETS:
                stat_value = repo.get_stat(market_con, stat)
                LOGGER.info(f"{market_con.value.upper()}-> {stat.value}={stat_value}")
        # don't need to fetch overall report
        return

    # candles data
    candles_data: List[List[str | float]] = [
        ["market", "close", "open", "high", "low", "vol"]
    ]
    if market:
        data = [market.value]
        candle = get_market_last_candle(repo, market)
        candles_data.append(data + candle)
    else:
        for market_con in settings.MARKETS:
            data = [market_con.value]
            candle = get_market_last_candle(repo, market_con)
            candles_data.append(data + candle)
    widths = [
        max(len(str(row[i])) for row in candles_data)
        for i in range(len(candles_data[0]))
    ]
    for row in candles_data:
        print(" | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))

    print("\n######################################################################\n")
    # stats data
    if market:
        print(f"{market=}")
        for item in MarketStat.__iter__():
            stat_value = repo.get_stat(market, item)
            if item == MarketStat.IS_UPDATED:
                stat_value = bool(stat_value)
            print(f"{item.name.lower()}={stat_value}")
    else:
        for market_con in settings.MARKETS:
            print(f"market={market_con}")
            for item in MarketStat.__iter__():
                stat_value = repo.get_stat(market_con, item)
                if item == MarketStat.IS_UPDATED:
                    stat_value = bool(stat_value)
                print(f"{item.name.lower()}={stat_value}")

            print(
                "\n######################################################################\n"
            )


def main():
    parser = argparse.ArgumentParser(description="Shared Memory Key/Value CLI")

    parser.add_argument(
        "--market", type=str, default=None, required=False, help="Read Market"
    )
    parser.add_argument(
        "--stat", type=str, default=None, required=False, help="Read Market Stat"
    )
    args = parser.parse_args()

    market = None
    market_stat = None
    if args.market:
        market = Market(args.market)
        if market not in settings.MARKETS:
            raise ValueError(f"this {args.market=} is not in configuration")
    if args.stat:
        market_stat = MarketStat[args.stat]
    repo = MonitoringSHMRepository(markets=settings.MARKETS)
    LOGGER.info(f"connected to the SHM")
    read_shm(repo, market, market_stat)
    repo.close()


if __name__ == "__main__":
    main()
