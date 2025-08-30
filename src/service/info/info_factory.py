from ...enums.data_type import DataType
from ...enums.exchange import Exchange
from ...enums.market import Market

from ..info import hyperliquid_info


def get_candle_snapshots(exchange: Exchange, market: Market, data_type: DataType):
    if exchange == Exchange.HYPERLIQUID:
        return hyperliquid_info.candle_snapshot(market, data_type.value)
    else:
        raise ValueError(f"There isn't indicator for {data_type.value}")
