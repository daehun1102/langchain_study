from abc import ABC, abstractmethod


class BaseAgent(ABC):

    def __init__(self):
        self.agent = None

    @abstractmethod
    def create_agent(self, tools: list = None): ...

    async def run(self, query: str, config: dict = None):
        if self.agent is None:
            raise ValueError("create_agent()를 먼저 호출하세요.")
        last_message = None
        async for event in self.agent.astream(
            {"messages": [{"role": "user", "content": query}]},
            config=config or {},
            stream_mode="values",
        ):
            last_message = event["messages"][-1]
        return last_message
