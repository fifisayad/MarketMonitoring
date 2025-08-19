from ..enums.data_type import DataType
from ..enums.market import Market


def data_type_to_type(
    data_type: DataType,
) -> str:
    if data_type == DataType.TRADES:
        return "trades"
    elif data_type == DataType.ORDERBOOK:
        return "l2Book"
    else:
        raise ValueError(f"there is no data type fo {data_type.value} in hyperliquid")


def market_to_hyper_market(market: Market) -> str:
    if market == Market.BTCUSD:
        return "BTC/USDC"
    elif market == Market.BTCUSD_PERP:
        return "BTC"
    else:
        raise ValueError(f"There is no market={market.value} in hyperliquid")
