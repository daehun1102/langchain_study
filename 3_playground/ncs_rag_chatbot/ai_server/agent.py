"""
agent.py — LangChain/LangGraph 기반 채팅 에이전트

Phase 3 변경:
- 하드코딩 시스템 프롬프트 제거
- Redis에서 프롬프트 로드 (prompt_loader.get_prompt)
- Redis 연결 실패 시 fallback 프롬프트 사용

Phase 3.1 변경:
- _build_system_prompt(): 5개 프롬프트를 결합하여 단일 system_prompt 생성
"""

from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from prompt_loader import get_prompt
from typing import List


PROMPT_KEYS = [
    "agent_system_prompt",
    "answer_format_prompt",
    "no_document_prompt",
    "query_enhance_prompt",
    "category_hint_prompt",
]


def _build_system_prompt() -> str:
    """Redis에서 5개 프롬프트를 로드하여 하나의 system prompt로 결합한다.

    Redis에서 키를 찾지 못하면 fallback 값을 사용한다.
    빈 문자열인 프롬프트는 결합에서 제외한다.
    """
    parts = [p for k in PROMPT_KEYS if (p := get_prompt(k))]
    return "\n\n".join(parts)


class ChatAgent:

    def __init__(self, model_name: str = "gpt-4o-mini", system_prompt: str = None):
        self.model = init_chat_model(model_name)
        # system_prompt가 명시적으로 전달되면 사용, 없으면 Redis 5개 통합 로드
        if system_prompt is not None:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = _build_system_prompt()

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

