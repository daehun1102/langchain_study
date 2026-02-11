import re
import json
from langgraph.types import interrupt
from semiconductor.state import GraphState
from semiconductor.agents import (
    photo_agent, etch_agent, deposition_agent,
    history_agent, router_agent, supervisor_agent,
    chat_agent,
)

SEMICONDUCTOR_KEYWORDS = re.compile(
    r'(LOT|lot|공정|photo|Photo|PHOTO|etch|Etch|ETCH|'
    r'deposition|Deposition|DEPOSITION|검사|패턴|CD|cd|'
    r'식각|증착|포토|웨이퍼|wafer|FAB|fab)',
    re.IGNORECASE,
)


def history_node(state: GraphState) -> GraphState:
    """History agent를 호출해서 LOT의 공정 이력을 요약."""
    user_request = state["user_request"]
    result = history_agent.invoke({
        "messages": [{"role": "user", "content": user_request}]
    })
    history_text = result["messages"][-1].content
    return {"history_summary": history_text}


def router_decision_node(state: GraphState) -> GraphState:
    """router_agent로 photo/etch/deposition 중 공정을 선택."""
    request = state["user_request"]
    history = state.get("history_summary", "")

    prompt = (
        "다음 반도체 LOT 요청과 이력 요약을 보고, "
        "'photo', 'etch', 'deposition' 중 하나의 공정을 선택해.\n\n"
        f"- 사용자 요청: {request}\n"
        f"- 이력 요약: {history}\n\n"
        "반드시 다음과 같은 JSON만 반환해:\n"
        '{ "process": "photo", "reason": "..." }'
    )

    result = router_agent.invoke({
        "messages": [{"role": "user", "content": prompt}]
    })
    content = result["messages"][-1].content

    try:
        routing_decision = json.loads(content)
    except Exception:
        routing_decision = {"process": "photo", "reason": "기본값(photo)으로 선택"}

    return {"routing_decision": routing_decision}


def router_hitl_node(state: GraphState) -> GraphState:
    """라우터가 공정을 선택한 후, 사람에게 검토를 요청한다."""
    request = state["user_request"]
    decision = state.get("routing_decision") or {}
    process = decision.get("process", "unknown")
    reason = decision.get("reason", "")

    human_review = interrupt({
        "action": "router_decision_review",
        "args": {
            "request": request,
            "process": process,
            "reason": reason,
        },
        "description": (
            f"라우터가 '{process}' 공정을 선택했습니다.\n"
            f"- 사유: {reason}\n"
            f"- 원본 요청: {request}\n\n"
            "승인, 거부, 또는 공정을 수정해 주세요."
        ),
    })

    if isinstance(human_review, dict):
        review_type = human_review.get("type", "approve")
        if review_type == "reject":
            msg = human_review.get("message", "사용자가 요청을 거부했습니다.")
            return {
                "router_human_review": human_review,
                "final_answer": f"요청이 거부되었습니다: {msg}",
            }
        elif review_type == "edit":
            # 공정 또는 요청을 수정
            new_args = human_review.get("args", {})
            new_process = new_args.get("process", process)
            new_reason = new_args.get("reason", reason)
            new_request = new_args.get("request", request)
            return {
                "router_human_review": human_review,
                "routing_decision": {"process": new_process, "reason": new_reason},
                "user_request": new_request,
            }

    # approve
    return {"router_human_review": human_review if isinstance(human_review, dict) else {"type": "approve"}}


def process_node(state: GraphState) -> GraphState:
    """routing_decision에 따라 photo/etch/deposition 에이전트 중 하나를 호출."""
    request = state["user_request"]
    decision = state.get("routing_decision") or {}
    process = decision.get("process", "photo")

    routed_request = f"{request} (선택된 공정: {process})"

    if process == "etch":
        agent = etch_agent
    elif process == "deposition":
        agent = deposition_agent
    else:
        agent = photo_agent

    result = agent.invoke({
        "messages": [{"role": "user", "content": routed_request}]
    })
    process_answer = result["messages"][-1].content

    return {
        "routed_request": routed_request,
        "process_result": process_answer,
    }


def supervisor_node(state: GraphState) -> GraphState:
    """history_summary + process_result를 종합해 최종 답변 생성."""
    if state.get("final_answer"):
        return {}

    request = state["user_request"]
    history = state.get("history_summary", "")
    process_result = state.get("process_result", "")

    prompt = (
        "다음은 사용자의 요청, LOT 공정 이력 요약, 그리고 선택된 공정의 검사 결과야.\n"
        "이 정보를 종합해서, 사용자가 이해하기 쉽게 한국어로 최종 결과를 요약해줘.\n\n"
        f"- 사용자 요청: {request}\n\n"
        f"- 이력 요약:\n{history}\n\n"
        f"- 공정 검사 결과:\n{process_result}\n"
    )

    result = supervisor_agent.invoke({
        "messages": [{"role": "user", "content": prompt}]
    })
    final_answer = result["messages"][-1].content

    return {"final_answer": final_answer}


def router_hitl_router(state: GraphState):
    """router_hitl 결과에 따라 분기: reject → END, approve/edit → process"""
    review = state.get("router_human_review")
    if isinstance(review, dict) and review.get("type") == "reject":
        return "end"
    return "process"


def classifier_node(state: GraphState) -> GraphState:
    """키워드 기반으로 semiconductor/chat 분류."""
    user_request = state.get("user_request", "")
    if SEMICONDUCTOR_KEYWORDS.search(user_request):
        return {"classification": "semiconductor"}
    return {"classification": "chat"}


def chat_node(state: GraphState) -> GraphState:
    """일반 대화용 chat_agent 호출."""
    user_request = state.get("user_request", "")
    result = chat_agent.invoke({
        "messages": [{"role": "user", "content": user_request}]
    })
    answer = result["messages"][-1].content
    return {"final_answer": answer}


def classifier_router(state: GraphState):
    """classification 값에 따라 history(반도체) 또는 chat 반환."""
    if state.get("classification") == "semiconductor":
        return "history"
    return "chat"
