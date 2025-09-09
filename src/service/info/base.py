from abc import ABC, abstractmethod


class BaseInfo(ABC):
    @abstractmethod
    async def candle_snapshot(self):
        """retrive candle snapshots from exchange"""
        pass
