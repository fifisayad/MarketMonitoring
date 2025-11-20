from fifi.repository.shm.market_data_repository import intervals_type


def to_time(interval: intervals_type) -> int:
    minute = 60 * 1000
    if interval == "1m":
        return minute
    elif interval == "5m":
        return 5 * minute
    elif interval == "30m":
        return 30 * minute
    elif interval == "1h":
        return 60 * minute
    elif interval == "1d":
        return 24 * 60 * minute
    elif interval == "1w":
        return 7 * 24 * 60 * minute
