"""
ai_server/agents/v2/supervisor.py — NCS Handoffs Agent

LangChain handoffs 패턴 적용:
- 단일 create_agent 인스턴스
- current_step 상태에 따라 middleware가 system_prompt + tools 동적 교체
- 3단계 순차 워크플로우: sql → rag → feedback
"""
from typing import Literal, Callable
from typing_extensions import NotRequired

from langchain.agents import AgentState, create_agent
from langchain.chat_models import init_chat_model
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agents.base import BaseAgent
from config import settings


# ── 상태 스키마 ────────────────────────────────────────────────

NCSStep = Literal["sql", "rag", "feedback"]


class NCSAgentState(AgentState):
    """NCS 피드백 워크플로우 상태."""
    current_step: NotRequired[NCSStep]


# ── 핸드오프 도구 ──────────────────────────────────────────────

@tool
def complete_sql_step(runtime: ToolRuntime[None, NCSAgentState]) -> Command:
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
def complete_rag_step(runtime: ToolRuntime[None, NCSAgentState]) -> Command:
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
    "너는 직원의 과제 내용을 조회하는 전문가야.\n"
    "사용자 메시지에서 사번(예: EMP001) 또는 직원 이름을 파악하여 "
    "query_employee_data 도구로 직원 이력을 조회해.\n"
    "조회가 완료되면:\n"
    "1. 결과를 보고 직원이 작성한 과제 내용을 사용자에게 마크다운 형식으로 보여줘\n"
    "2. 그리고 어떤 NCS 항목 또는 키워드를 기준으로 자료를 가져올지 물어봐\n"
    "생성을 다했으면 complete_sql_step 도구를 호출해서 다음 단계로 전환해\n"
)

RAG_STEP_PROMPT = (
    "너는 NCS 문서 검색 전문가야.\n"
    "직전 대화에서 직원 이력이 조회되었어.\n"
    "사용자가 어떤 NCS 항목, 키워드를 선택할건지 답변한 내용을 바탕으로:\n"
    "1. retrieve_context 도구로 관련 NCS 기준 문서를 검색해\n"
    "2. 검색 결과 중 가장 관련성이 높고 피드백에 도움이 될만한 내용을 사용자에게 마크다운 형식으로 보여줘.\n"
    "3. 그리고 사용자에게 어떤 관점(예: 강점 중심 / 개선점 중심 / 균형 있게) 으로 피드백을 작성할지 물어봐\n"
    "생성을 다했으면 complete_rag_step 도구를 호출해서 다음 단계로 전환해\n"
)

FEEDBACK_STEP_PROMPT = (
    "너는 NCS 직원 관리 피드백 전문가야.\n"
    "이전 대화에서 수집된 직원 이력 데이터와 NCS 문서 검색 결과를 확인했다.\n"
    "(예: 강점 중심 / 개선점 중심 / 균형 있게).\n"
    "사용자가 방향을 제시하면 마크다운 형식으로 종합 피드백을 작성해줘.\n"
    "직원 이력과 NCS 기준을 항목별로 비교하고 구체적인 개선 방향을 제시해줘.\n"
    "불확실한 내용은 반드시 명시해."
)


# ── NCSHandoffAgent ────────────────────────────────────────────

class NCSHandoffAgent(BaseAgent):
    """handoffs 패턴 기반 NCS 피드백 에이전트.

    단일 LangGraph 에이전트 인스턴스가 current_step 상태에 따라
    sql → rag → feedback 3단계 순차 워크플로우를 수행한다.

    Note:
        각 단계(RAG, Feedback)는 사용자 입력을 기다리는 multi-turn 구조다.
        run() 호출 시 반드시 동일한 thread_id를 유지해야 대화 컨텍스트가 보존된다.
    """

    def __init__(self, rag_tools: list, sql_tools: list, model_name: str = None):
        self.model = init_chat_model(model_name or settings.model_name)
        self._rag_tools = rag_tools
        self._sql_tools = sql_tools
        self.checkpointer = InMemorySaver()

    def create_agent(self, tools: list = None):
        if tools is not None:
            raise ValueError(
                "NCSHandoffAgent does not support external tool override. "
                "Pass sql_tools and rag_tools to __init__ instead."
            )

        # 단계별 설정을 인스턴스 범위 클로저로 구성 (전역 상태 없음)
        step_config = {
            "sql": {
                "prompt": SQL_STEP_PROMPT,
                "tools": self._sql_tools + [complete_sql_step],
            },
            "rag": {
                "prompt": RAG_STEP_PROMPT,
                "tools": self._rag_tools + [complete_rag_step],
            },
            "feedback": {
                "prompt": FEEDBACK_STEP_PROMPT,
                "tools": [],
            },
        }

        @wrap_model_call
        async def apply_ncs_step_config(
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse],
        ) -> ModelResponse:
            """current_step에 따라 system_prompt와 tools를 매 모델 호출 전에 교체한다."""
            current_step = request.state.get("current_step", "sql")
            config = step_config[current_step]
            request = request.override(
                system_prompt=config["prompt"],
                tools=config["tools"],
            )
            return await handler(request)

        all_tools = self._sql_tools + self._rag_tools + [complete_sql_step, complete_rag_step]

        self.agent = create_agent(
            self.model,
            tools=all_tools,
            state_schema=NCSAgentState,
            middleware=[apply_ncs_step_config],
            checkpointer=self.checkpointer,
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
