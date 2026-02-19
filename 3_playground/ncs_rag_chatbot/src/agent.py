"""
agent.py — LangChain/LangGraph 기반 채팅 에이전트

Phase 2 변경:
- create_react_agent (langgraph.prebuilt) 사용
- 시스템 프롬프트에서 Phase 1 메타데이터 필터 설명 제거
- Phase 3에서 시스템 프롬프트를 Redis에서 로드할 예정 (현재는 하드코딩 유지)
"""

from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from typing import List


DEFAULT_SYSTEM_PROMPT = (
    "너는 NCS(국가직무능력표준) 문서에서 정보를 검색하여 답변해주는 친절한 AI 어시스턴트야.\n"
    "사용자의 질의에 retrieve_context 도구를 적극적으로 사용해서 답변해줘.\n"
    "답변할 때 검색된 문서의 내용을 바탕으로 정확하게 답변하고, "
    "관련 내용의 페이지 정보를 언급해줘."
)


class ChatAgent:

    def __init__(self, model_name: str = "gpt-4o-mini", system_prompt: str = None):
        self.model = init_chat_model(model_name)
        self.system_prompt = system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT

    def create_agent(self, tools: List):
        """모델과 도구를 결합하여 ReAct 에이전트를 생성한다."""
        self.agent = create_react_agent(
            self.model,
            tools,
            prompt=self.system_prompt,
        )

    async def run(self, query: str):
        """사용자 질의를 처리하고 마지막 메시지를 반환한다."""
        if not hasattr(self, "agent"):
            raise ValueError("Agent가 생성되지 않았습니다. create_agent()를 먼저 호출하세요.")

        last_message = None
        async for event in self.agent.astream(
            {"messages": [{"role": "user", "content": query}]},
            stream_mode="values",
        ):
            last_message = event["messages"][-1]

        return last_message
