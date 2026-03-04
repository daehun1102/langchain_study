# display_defect_chatbot/ai_server/agents/graph.py
"""
LangGraph Send API 병렬 서브에이전트 그래프

흐름: START → [Send API 병렬 팬아웃] → 4개 서브에이전트 → synthesis → END
"""
from typing import Annotated, TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.memory import InMemorySaver


def replace_list(current: list, update: list) -> list:
    """서브에이전트 결과 reducer: 새 값으로 교체 (operator.add 누적 방지)"""
    return update

from ai_server.agents.sub.process_history import process_history_node
from ai_server.agents.sub.return_history import return_history_node
from ai_server.agents.sub.test_result import test_result_node
from ai_server.agents.sub.long_term import long_term_node
from ai_server.agents.synthesis_node import synthesis_node


class DefectAnalysisState(TypedDict):
    # 입력
    company: str
    defect_description: str
    product_id: str
    selected_hypothesis: str
    session_id: str

    # 병렬 서브에이전트 결과 (replace_list reducer: 재호출 시 이전 값 교체)
    process_history_result: Annotated[list, replace_list]
    return_history_result: Annotated[list, replace_list]
    test_result: Annotated[list, replace_list]
    long_term_task_id: Annotated[list, replace_list]

    # 최종 출력
    final_action_plan: str


def route_to_agents(state: DefectAnalysisState) -> list[Send]:
    """Send API: 4개 서브에이전트로 병렬 팬아웃"""
    sub_state = dict(state)
    return [
        Send("process_history_node", sub_state),
        Send("return_history_node", sub_state),
        Send("test_result_node", sub_state),
        Send("long_term_node", sub_state),
    ]


def build_investigation_graph():
    builder = StateGraph(DefectAnalysisState)

    builder.add_node("process_history_node", process_history_node)
    builder.add_node("return_history_node", return_history_node)
    builder.add_node("test_result_node", test_result_node)
    builder.add_node("long_term_node", long_term_node)
    builder.add_node("synthesis", synthesis_node)

    # START → Send API 병렬 팬아웃
    builder.add_conditional_edges(START, route_to_agents)

    # 각 서브에이전트 → synthesis
    builder.add_edge("process_history_node", "synthesis")
    builder.add_edge("return_history_node", "synthesis")
    builder.add_edge("test_result_node", "synthesis")
    builder.add_edge("long_term_node", "synthesis")

    builder.add_edge("synthesis", END)

    checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)


# 앱 시작 시 단일 인스턴스 생성
investigation_graph = build_investigation_graph()
