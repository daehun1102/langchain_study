from abc import ABC, abstractmethod


class BaseAgent(ABC):

    @abstractmethod
    def create_agent(self, tools: list): ...

    @abstractmethod
    async def run(self, query: str, config: dict = None): ...
