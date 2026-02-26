"""
scripts/visualize_graphs.py — Agent 그래프 구조를 PNG로 저장

실행 방법:
    cd ai_server
    python ../scripts/visualize_graphs.py

출력:
    docs/v1_graph.png  — SupervisorAgent (표준 ReAct)
    docs/v2_graph.png  — NCSHandoffAgent (커스텀 state + middleware ReAct)

주의: draw_mermaid_png()는 Mermaid.ink 외부 API를 사용하므로 인터넷 연결 필요.
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트의 .env 로드 (API 키 등)
ROOT = Path(__file__).parent.parent
env_file = ROOT / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

# ai_server 패키지를 찾을 수 있도록 경로 추가
sys.path.insert(0, str(ROOT / "ai_server"))

from typing import Literal
from typing_extensions import NotRequired

from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

DOCS_DIR = Path(__file__).parent.parent / "docs"


# ── 더미 도구 (그래프 구조 확인용, API 호출 없음) ──────────────

@tool
def dummy_rag(query: str) -> str:
    """NCS 문서 검색 (dummy)"""
    return ""

@tool
def dummy_sql(identifier: str) -> str:
    """직원 이력 조회 (dummy)"""
    return ""


# ── 모델 (그래프 빌드 시 API 호출 없음) ───────────────────────

model = init_chat_model("gpt-4o-mini")


# ── v1: SupervisorAgent 구조 ───────────────────────────────────

v1_agent = create_agent(
    model,
    [dummy_rag, dummy_sql],
    checkpointer=InMemorySaver(),
)

v1_png = v1_agent.get_graph().draw_mermaid_png()
out_v1 = DOCS_DIR / "v1_graph.png"
out_v1.write_bytes(v1_png)
print(f"saved: {out_v1}")


# ── v2: NCSHandoffAgent 구조 ──────────────────────────────────


class NCSAgentState(AgentState):
    """v2 에이전트 상태 (current_step 포함)"""
    current_step: NotRequired[Literal["sql", "rag", "feedback"]]


@wrap_model_call
async def _noop_middleware(
    request: ModelRequest,
    handler,
) -> ModelResponse:
    """구조 확인용 no-op 미들웨어 (apply_ncs_step_config 역할만 표현)"""
    return await handler(request)


v2_agent = create_agent(
    model,
    [dummy_rag, dummy_sql],
    state_schema=NCSAgentState,
    middleware=[_noop_middleware],
    checkpointer=InMemorySaver(),
)

v2_png = v2_agent.get_graph().draw_mermaid_png()
out_v2 = DOCS_DIR / "v2_graph.png"
out_v2.write_bytes(v2_png)
print(f"saved: {out_v2}")
