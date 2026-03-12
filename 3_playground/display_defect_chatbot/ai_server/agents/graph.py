# ai_server/agents/graph.py
"""
Stateful LangGraph — interrupt()/Command(resume=...) + AsyncPostgresSaver

흐름:
  START → hypothesis_node (interrupt: hypotheses 반환)
        → investigation_dispatch (Send API 병렬)
        → await_long_term_node (interrupt: agent_results + task_id 반환)
        → final_synthesis_node
        → chat_node (interrupt loop: Q&A)
"""
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START
from langgraph.types import Send, interrupt

from ai_server.agents.prompts import (
    HYPOTHESIS_SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
)
from ai_server.agents.state import DefectAnalysisState, SubAgentInput, HypothesesResponse
from ai_server.agents.sub.process_history import process_history_node
from ai_server.agents.sub.return_history import return_history_node
from ai_server.agents.sub.test_history import test_history_node
from ai_server.agents.sub.long_term import long_term_node
from ai_server.agents.synthesis_node import final_synthesis_node
from ai_server.config import get_settings
from ai_server.infra.graph_logger import apply_middleware, build_node_middleware
from ai_server.infra.vector_store import VectorStoreManager

settings = get_settings()
_llm = ChatOpenAI(model=settings.model_name, temperature=0.3)
_chat_llm = ChatOpenAI(model=settings.model_name, temperature=0.5)
_hypothesis_llm = _llm.with_structured_output(HypothesesResponse)

_INPUT_KEYS = tuple(SubAgentInput.__annotations__)

_NODE_MAP = {
    "process_history": "process_history_node",
    "return_history":  "return_history_node",
    "test_history":    "test_history_node",
    "long_term":       "long_term_node",
}
ALL_AGENTS: list[str] = list(_NODE_MAP.keys())


# ── 노드 정의 ──────────────────────────────────────────────────────────────

async def hypothesis_node(state: DefectAnalysisState, config: RunnableConfig) -> dict:
    """RAG 검색 → structured output으로 가설+추천 에이전트 생성 → interrupt → 선택된 가설 수신"""
    vsm: VectorStoreManager = config["configurable"]["vsm"]
    docs = await vsm.similarity_search(state["defect_description"], k=4)
    context = "\n\n".join([d.page_content for d in docs]) if docs else "관련 사례 없음"

    messages = [
        SystemMessage(content=HYPOTHESIS_SYSTEM_PROMPT),
        HumanMessage(
            content=f"[보고 회사]: {state['company']}\n[불량 증상]: {state['defect_description']}\n\n[과거 사례 문서]\n{context}"
        ),
    ]
    response: HypothesesResponse = await _hypothesis_llm.ainvoke(messages)
    hypotheses_data = [h.model_dump() for h in response.hypotheses]

    # interrupt: 클라이언트에 가설 목록(text + recommended_agents) 반환
    # resume 값은 {"selected_hypothesis": str, "enabled_agents": list} 형태의 dict
    resume = interrupt({"hypotheses": hypotheses_data})

    if isinstance(resume, dict):
        selected = resume.get("selected_hypothesis", "")
        enabled = resume.get("enabled_agents")
    else:
        selected = str(resume)
        enabled = None

    result: dict = {"hypotheses": hypotheses_data, "selected_hypothesis": selected}
    if enabled is not None:
        result["enabled_agents"] = enabled
    if isinstance(resume, dict) and resume.get("notify_email") is not None:
        result["notify_email"] = resume["notify_email"]
    return result


def route_to_agents(state: DefectAnalysisState) -> list[Send]:
    """Send API: enabled_agents에 포함된 에이전트만 병렬 팬아웃"""
    sub_state = {k: state[k] for k in _INPUT_KEYS}
    enabled = state.get("enabled_agents") or ALL_AGENTS
    return [Send(_NODE_MAP[key], sub_state) for key in enabled if key in _NODE_MAP]


async def await_long_term_node(state: DefectAnalysisState) -> dict:
    """병렬 에이전트 완료 후 interrupt: agent_results + task_id 반환, 장기이력 결과 수신
    long_term이 비활성(task_id 없음)이면 interrupt 없이 바로 통과."""
    agent_results = {
        "process_history": state.get("process_history_result"),
        "return_history":  state.get("return_history_result"),
        "test_history":    state.get("test_history_result"),
    }
    task_id = state.get("long_term_task_id")

    if task_id:
        # long_term이 실행된 경우: 프론트 폴링 완료 후 resume 대기
        long_term_result: str = interrupt({
            "agent_results": agent_results,
            "long_term_task_id": task_id,
        })
        return {"long_term_result": long_term_result}
    else:
        # long_term 미실행: 즉시 agent_results만 반환, interrupt 없이 통과
        # 프론트에 결과를 전달하기 위해 별도 interrupt
        interrupt({"agent_results": agent_results, "long_term_task_id": None})
        return {"long_term_result": ""}


async def chat_node(state: DefectAnalysisState) -> dict:
    """Q&A 루프: interrupt로 user_message 수신 → LLM 응답 → 메시지 누적"""
    user_message: str = interrupt({"final_action_plan": state.get("final_action_plan", "")})

    context = f"""[최종 조치안]
{state.get('final_action_plan', '')}

[불량 증상]: {state['defect_description']}
[선택된 가설]: {state.get('selected_hypothesis', '')}"""

    messages = [
        SystemMessage(content=CHAT_SYSTEM_PROMPT + "\n\n" + context),
        *state.get("messages", []),
        HumanMessage(content=user_message),
    ]
    response = await _chat_llm.ainvoke(messages)

    return {
        "messages": [
            HumanMessage(content=user_message),
            AIMessage(content=response.content),
        ]
    }


# ── 그래프 빌드 ────────────────────────────────────────────────────────────

def build_investigation_graph(checkpointer):
    builder = StateGraph(DefectAnalysisState)
    mw = build_node_middleware(settings)

    builder.add_node("hypothesis_node",       apply_middleware(hypothesis_node,       "hypothesis_node",       mw))
    builder.add_node("process_history_node",  apply_middleware(process_history_node,  "process_history_node",  mw))
    builder.add_node("return_history_node",   apply_middleware(return_history_node,   "return_history_node",   mw))
    builder.add_node("test_history_node",     apply_middleware(test_history_node,     "test_history_node",     mw))
    builder.add_node("long_term_node",        apply_middleware(long_term_node,        "long_term_node",        mw))
    builder.add_node("await_long_term_node",  apply_middleware(await_long_term_node,  "await_long_term_node",  mw))
    builder.add_node("final_synthesis_node",  apply_middleware(final_synthesis_node,  "final_synthesis_node",  mw))
    builder.add_node("chat_node",             apply_middleware(chat_node,             "chat_node",             mw))

    # START → hypothesis → Send API 병렬
    builder.add_edge(START, "hypothesis_node")
    builder.add_conditional_edges("hypothesis_node", route_to_agents)

    # 병렬 에이전트 → await_long_term (LangGraph: 모든 선행 노드 완료 후 실행)
    builder.add_edge("process_history_node", "await_long_term_node")
    builder.add_edge("return_history_node",  "await_long_term_node")
    builder.add_edge("test_history_node",    "await_long_term_node")
    builder.add_edge("long_term_node",       "await_long_term_node")

    # await_long_term → synthesis → chat (loop)
    builder.add_edge("await_long_term_node", "final_synthesis_node")
    builder.add_edge("final_synthesis_node", "chat_node")
    builder.add_edge("chat_node", "chat_node")  # Q&A 루프

    return builder.compile(checkpointer=checkpointer)
