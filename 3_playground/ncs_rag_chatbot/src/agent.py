from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from typing import List

class ChatAgent:
    """채팅 에이전트를 생성하고 실행하는 클래스"""

    def __init__(self, model_name: str = "gpt-4o-mini", system_prompt: str = None):
        self.model = init_chat_model(model_name)
        if system_prompt is None:
            self.system_prompt = (
                "너는 PDF 파일에서 정보를 검색하여 답변해주는 친절한 AI 어시스턴트야."
                "사용자의 질의에 retrieve_context 도구를 적극적으로 사용해서 답변해줘."
            )
        else:
            self.system_prompt = system_prompt

    def create_agent(self, tools: List):
        """모델과 도구를 결합하여 에이전트를 생성합니다."""
        self.agent = create_agent(self.model, tools, system_prompt=self.system_prompt)
    
    async def run(self, query: str):
        """사용자 질의를 처리하고 답변을 생성합니다. (Async)"""
        if not hasattr(self, 'agent'):
            raise ValueError("Agent has not been created. Call create_agent() first.")

        print(f"User Query: {query}")
        print("--- Agent Response ---")
        
        last_message = None
        # astream을 사용하여 비동기 스트리밍 처리
        async for event in self.agent.astream(
            {"messages": [{"role": "user", "content": query}]},
            stream_mode="values",
        ):
            event["messages"][-1].pretty_print()
            last_message = event["messages"][-1]
        
        return last_message
