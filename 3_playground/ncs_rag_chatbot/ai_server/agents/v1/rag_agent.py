"""
rag_agent.py — NCS 문서 검색 전문 에이전트

변경:
- agent.py에서 이동
- InMemorySaver checkpointer로 multi-turn 지원
- RunnableConfig로 doc_ids 런타임 주입 (rag_tool.py의 retrieve_context가 읽음)
"""
import langchain.agents as _lc_agents
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from agents.base import BaseAgent
from infra.prompt_loader import get_prompt
from typing import List


PROMPT_KEYS = [
    "agent_system_prompt",
    "answer_format_prompt",
    "no_document_prompt",
    "query_enhance_prompt",
    "category_hint_prompt",
]


def _build_system_prompt() -> str:
    parts = [p for k in PROMPT_KEYS if (p := get_prompt(k))]
    return "\n\n".join(parts)


class ChatAgent(BaseAgent):

    def __init__(self, model_name: str = "gpt-4o-mini", system_prompt: str = None):
        super().__init__()
        self.model = init_chat_model(model_name)
        self.checkpointer = InMemorySaver()
        self.system_prompt = system_prompt if system_prompt is not None else _build_system_prompt()

    def create_agent(self, tools: List = None):
        self.agent = _lc_agents.create_agent(
            self.model,
            tools,
            system_prompt=self.system_prompt,
            checkpointer=self.checkpointer,
        )
