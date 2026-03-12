# ai_server/agents/registry.py
"""
에이전트 식별자 단일 진실 공급원 (Single Source of Truth).

에이전트를 추가하거나 rename할 때 이 파일만 수정하면 된다.
"""
from enum import StrEnum


class AgentKey(StrEnum):
    """에이전트 식별자 Enum. 값은 API·DB·프론트엔드 계약 문자열과 일치."""
    PROCESS_HISTORY = "process_history"
    RETURN_HISTORY  = "return_history"
    TEST_HISTORY    = "test_history"
    LONG_TERM       = "long_term"


# LangGraph 노드 이름 매핑 — graph.py가 이를 참조한다.
AGENT_NODE_MAP: dict[AgentKey, str] = {
    AgentKey.PROCESS_HISTORY: "process_history_node",
    AgentKey.RETURN_HISTORY:  "return_history_node",
    AgentKey.TEST_HISTORY:    "test_history_node",
    AgentKey.LONG_TERM:       "long_term_node",
}
