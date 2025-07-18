from abc import ABC, abstractmethod


class BaseExchangeWorker(ABC):
    def __init__(self, pair: str, redis_channel: str, data_type: str = "trades"):
        self.pair = pair
        self.data_type = data_type
        self.redis_channel = redis_channel

    @abstractmethod
    async def connect(self):
        """Establish WebSocket connection"""
        pass

    @abstractmethod
    async def listen(self):
        """Listen to incoming data and publish to Redis"""
        pass

    @abstractmethod
    async def run(self):
        """Main loop: connect and start listening"""
        pass

    @abstractmethod
    async def stop(self):
        """Cleanup tasks and shutdown logic"""
        pass

    def get_key(self) -> str:
        """unique id for worker"""
        return f"{self.__class__.__name__}-{self.pair}-{self.data_type}"
