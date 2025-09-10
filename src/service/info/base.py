from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseInfo(ABC):
    @abstractmethod
    def candle_snapshot(self, *args, **kwargs) -> List[Dict[Any, Any]]:
        """retrive candle snapshots from exchange"""
        pass
