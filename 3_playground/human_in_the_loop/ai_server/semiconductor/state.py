from typing import TypedDict, Optional, Dict, Any


class GraphState(TypedDict, total=False):
    # 입력
    user_request: str
    # 분류
    classification: Optional[str]
    # 중간 결과
    history_summary: Optional[str]
    routing_decision: Optional[Dict[str, Any]]
    routed_request: Optional[str]
    # 최종 결과
    process_result: Optional[str]
    final_answer: Optional[str]
    # Human-in-the-loop
    router_human_review: Optional[Dict[str, Any]]
