# ai_server/agents/state.py
"""
그래프 상태 TypedDict 정의.

graph.py ↔ 서브에이전트 / synthesis_node 간 circular import를 막기 위해
TypedDict를 별도 모듈로 분리.
"""
from typing import Annotated, Literal, Optional, TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class AgentOutputSchema(BaseModel):
    """with_structured_output용 Pydantic 스키마 (sub-agent 3종 공통)"""
    suspect_rows: list = Field(description="문제 원인으로 의심되는 row들 (원본 데이터 형식 그대로)")
    analysis: str = Field(description="에이전트 분석 결과 텍스트 2-3문장")


class HypothesisItem(BaseModel):
    """가설 하나와 추천 에이전트 목록"""
    text: str = Field(description="가설 텍스트")
    recommended_agents: list[Literal["process_history", "return_history", "test_result", "long_term"]] = Field(
        description="추천 에이전트 목록"
    )


class HypothesesResponse(BaseModel):
    """hypothesis_node structured output 스키마"""
    hypotheses: list[HypothesisItem]


class SubAgentInput(TypedDict):
    """Send API로 서브에이전트에 전달되는 입력 전용 상태"""
    company: str
    defect_description: str
    product_id: str
    selected_hypothesis: str
    session_id: str
    notify_email: Optional[str]


class AgentAnalysisResult(TypedDict):
    """각 분석 에이전트의 결과: 의심 row 목록 + 분석 텍스트"""
    suspect_rows: list
    analysis: str


class DefectAnalysisState(TypedDict):
    """전체 그래프 상태"""

    # ── 입력 (불변) ──────────────────────────
    company: str
    defect_description: str
    product_id: str
    session_id: str
    enabled_agents: list[str]
    notify_email: Optional[str]

    # ── 가설 단계 ────────────────────────────
    hypotheses: list[dict]  # [{"text": str, "recommended_agents": list[str]}]
    selected_hypothesis: str

    # ── 에이전트 결과 (reducer: 최신값으로 교체) ──
    process_history_result: Annotated[Optional[AgentAnalysisResult], lambda _, u: u]
    return_history_result:  Annotated[Optional[AgentAnalysisResult], lambda _, u: u]
    test_result:            Annotated[Optional[AgentAnalysisResult], lambda _, u: u]
    long_term_task_id:      Annotated[Optional[str], lambda _, u: u]
    long_term_result:       Annotated[Optional[str], lambda _, u: u]

    # ── 최종 출력 ────────────────────────────
    final_action_plan: str

    # ── Q&A 대화 이력 (add_messages reducer로 누적) ──
    messages: Annotated[list[AnyMessage], add_messages]
