from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from semiconductor.state import GraphState
from semiconductor.nodes import (
    classifier_node,
    classifier_router,
    chat_node,
    history_node,
    router_decision_node,
    router_hitl_node,
    process_node,
    supervisor_node,
    router_hitl_router,
)

checkpointer = MemorySaver()

workflow = StateGraph(GraphState)

# 노드 등록
workflow.add_node("classifier", classifier_node)
workflow.add_node("chat", chat_node)
workflow.add_node("history", history_node)
workflow.add_node("router_decision", router_decision_node)
workflow.add_node("router_hitl", router_hitl_node)
workflow.add_node("process", process_node)
workflow.add_node("supervisor", supervisor_node)

# 엣지 정의
workflow.set_entry_point("classifier")
workflow.add_conditional_edges(
    "classifier",
    classifier_router,
    {
        "chat": "chat",
        "history": "history",
    },
)
workflow.add_edge("chat", END)
workflow.add_edge("history", "router_decision")
workflow.add_edge("router_decision", "router_hitl")
workflow.add_conditional_edges(
    "router_hitl",
    router_hitl_router,
    {
        "process": "process",
        "end": END,
    },
)
workflow.add_edge("process", "supervisor")
workflow.add_edge("supervisor", END)

# 그래프 컴파일
graph = workflow.compile(checkpointer=checkpointer)
