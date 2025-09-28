from abc import ABC

from fifi import BaseEngine
from fifi.enums import Exchange, Market

from ...common.settings import Settings


class BaseIndicator(BaseEngine, ABC):
    exchange: Exchange
    market: Market
    indicator_name: str
    pk: str

    def __init__(
        self, market: Market, exchange: Exchange, run_in_process: bool = False
    ):
        super().__init__(run_in_process)
        self.market = market
        self.exchange = exchange
        self.name = (
            f"{self.exchange.value}_{self.market.value}_{self.indicator_name}_engine"
        )
        self.pk = f"{self.exchange.value}_{self.market.value}_{self.indicator_name}"
        self.settings = Settings()

    async def subscribe(self) -> str:
        return self.pk
