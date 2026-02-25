"""
ai_server/agents/v2/supervisor.py — NCS Handoffs Agent

LangChain handoffs 패턴 적용:
- 단일 create_agent 인스턴스
- current_step 상태에 따라 middleware가 system_prompt + tools 동적 교체
- 3단계 순차 워크플로우: sql → rag → feedback
"""
from typing import Literal, Callable

import langchain.agents as _lc_agents
import langchain.chat_models as _lc_chat
from langchain.agents import AgentState
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from typing_extensions import NotRequired

from agents.base import BaseAgent
from config import settings


# ── 상태 스키마 ────────────────────────────────────────────────

NCSStep = Literal["sql", "rag", "feedback"]


class NCSAgentState(AgentState):
    """NCS 피드백 워크플로우 상태."""
    current_step: NotRequired[NCSStep]


# ── 핸드오프 도구 ──────────────────────────────────────────────

@tool
def handoff_to_rag(runtime: ToolRuntime[None, NCSAgentState]) -> Command:
    """직원 이력 조회 완료 후 NCS 문서 검색 단계로 전환한다."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content="직원 이력 수집 완료. NCS 문서 검색 단계로 전환합니다.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "current_step": "rag",
        }
    )


@tool
def handoff_to_feedback(runtime: ToolRuntime[None, NCSAgentState]) -> Command:
    """NCS 문서 검색 완료 후 종합 피드백 생성 단계로 전환한다."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content="NCS 문서 검색 완료. 종합 피드백 생성 단계로 전환합니다.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "current_step": "feedback",
        }
    )


# ── 단계별 프롬프트 ────────────────────────────────────────────

SQL_STEP_PROMPT = (
    "너는 NCS 직원 이력 조회 전문가야.\n"
    "사용자 메시지에서 사번(예: EMP001) 또는 직원 이름을 파악하여 "
    "query_employee_data 도구로 이력을 조회해.\n"
    "조회가 완료되면 반드시 handoff_to_rag 도구를 호출해서 NCS 문서 검색 단계로 전환해."
)

RAG_STEP_PROMPT = (
    "너는 NCS 문서 검색 전문가야.\n"
    "사용자 메시지와 이전 직원 이력 데이터를 참고해서 "
    "retrieve_context 도구로 관련 NCS 기준 문서를 검색해.\n"
    "검색이 완료되면 반드시 handoff_to_feedback 도구를 호출해서 피드백 생성 단계로 전환해."
)

FEEDBACK_STEP_PROMPT = (
    "너는 NCS 직원 관리 피드백 전문가야.\n"
    "이전 대화에서 수집된 직원 이력 데이터와 NCS 문서 검색 결과를 바탕으로 "
    "종합적이고 건설적인 피드백을 마크다운 형식으로 작성해줘.\n"
    "직원 이력과 NCS 기준을 항목별로 비교하고 구체적인 개선 방향을 제시해줘.\n"
    "불확실한 내용은 반드시 명시해."
)


# ── 단계별 설정 ────────────────────────────────────────────────

STEP_CONFIG: dict = {
    "sql": {
        "prompt": SQL_STEP_PROMPT,
        "tools": [],   # create_agent()에서 sql_tools + [handoff_to_rag] 로 채워진다
    },
    "rag": {
        "prompt": RAG_STEP_PROMPT,
        "tools": [],   # create_agent()에서 rag_tools + [handoff_to_feedback] 로 채워진다
    },
    "feedback": {
        "prompt": FEEDBACK_STEP_PROMPT,
        "tools": [],   # 최종 답변 생성, 도구 불필요
    },
}


# ── 미들웨어 ───────────────────────────────────────────────────

@wrap_model_call
async def apply_ncs_step_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """current_step에 따라 system_prompt와 tools를 매 모델 호출 전에 교체한다."""
    current_step = request.state.get("current_step", "sql")
    config = STEP_CONFIG[current_step]
    request = request.override(
        system_prompt=config["prompt"],
        tools=config["tools"],
    )
    return await handler(request)


# ── NCSHandoffAgent ────────────────────────────────────────────

class NCSHandoffAgent(BaseAgent):
    """handoffs 패턴 기반 NCS 피드백 에이전트.

    단일 create_agent 인스턴스가 current_step 상태에 따라
    sql → rag → feedback 3단계 순차 워크플로우를 수행한다.
    """

    def __init__(self, rag_tools: list, sql_tools: list, model_name: str = None):
        self.model = _lc_chat.init_chat_model(model_name or settings.model_name)
        self._rag_tools = rag_tools
        self._sql_tools = sql_tools

    def create_agent(self, tools: list = None):
        # 단계별 도구 조합을 STEP_CONFIG에 주입
        STEP_CONFIG["sql"]["tools"] = self._sql_tools + [handoff_to_rag]
        STEP_CONFIG["rag"]["tools"] = self._rag_tools + [handoff_to_feedback]
        STEP_CONFIG["feedback"]["tools"] = []

        all_tools = self._sql_tools + self._rag_tools + [handoff_to_rag, handoff_to_feedback]

        self.agent = _lc_agents.create_agent(
            self.model,
            tools=all_tools,
            state_schema=NCSAgentState,
            middleware=[apply_ncs_step_config],
            checkpointer=InMemorySaver(),
        )

    async def run(self, query: str, config: dict = None):
        if not hasattr(self, "agent"):
            raise ValueError("create_agent()를 먼저 호출하세요.")
        last_message = None
        async for event in self.agent.astream(
            {"messages": [{"role": "user", "content": query}]},
            config=config or {},
            stream_mode="values",
        ):
            last_message = event["messages"][-1]
        return last_message
