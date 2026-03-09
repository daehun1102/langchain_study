# ai_server/server.py
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from langchain_openai import OpenAIEmbeddings
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
import os
import tempfile

from ai_server.agents.graph import build_investigation_graph, ALL_AGENTS, DefectAnalysisState
from ai_server.config import get_settings
from ai_server.infra.checkpointer import create_checkpointer
from ai_server.infra.ingest import ingest_document
from ai_server.infra.vector_store import VectorStoreManager
from ai_server.tools.sql_tools import get_bg_task

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    embedding = OpenAIEmbeddings(model=settings.embedding_model)
    app.state.vsm = await VectorStoreManager.create(settings.pg_async_url, embedding)
    app.state.checkpointer = await create_checkpointer(settings.pg_checkpoint_url)
    app.state.graph = build_investigation_graph(app.state.checkpointer)
    yield


app = FastAPI(title="Defect AI Server", lifespan=lifespan)


# ── Request / Response Models ──────────────────────────────────────────────

class AgentRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    session_id: str
    action: str  # "start" | "select_hypothesis" | "resume_long_term" | "chat"
    company: str = ""
    defect_description: str = ""
    product_id: str = ""
    enabled_agents: list[str] = list(ALL_AGENTS)
    # action별 선택 필드
    selected_hypothesis: Optional[str] = None
    long_term_result: Optional[str] = None
    user_message: Optional[str] = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    action: str
    # start
    hypotheses: Optional[list[str]] = None
    # select_hypothesis
    agent_results: Optional[dict] = None
    long_term_task_id: Optional[str] = None
    # resume_long_term
    final_action_plan: Optional[str] = None
    # chat
    reply: Optional[str] = None


class BgStatusResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    task_id: str
    status: str
    result_text: Optional[str] = None


# ── 헬퍼 ───────────────────────────────────────────────────────────────────

def _parse_interrupt(result: dict) -> dict:
    """graph.ainvoke() 반환값에서 interrupt value 추출"""
    interrupts = result.get("__interrupt__", [])
    if interrupts:
        return interrupts[0].value
    return {}


def _build_response(interrupt_value: dict, action: str) -> AgentResponse:
    if "hypotheses" in interrupt_value:
        return AgentResponse(action="start", hypotheses=interrupt_value["hypotheses"])
    if "agent_results" in interrupt_value:
        return AgentResponse(
            action="select_hypothesis",
            agent_results=interrupt_value["agent_results"],
            long_term_task_id=interrupt_value.get("long_term_task_id"),
        )
    if "final_action_plan" in interrupt_value:
        return AgentResponse(action="resume_long_term", final_action_plan=interrupt_value["final_action_plan"])
    return AgentResponse(action=action)


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.post("/internal/agent", response_model=AgentResponse, response_model_by_alias=True)
async def agent_endpoint(req: AgentRequest, request: Request):
    """단일 엔드포인트: action에 따라 그래프 start 또는 resume"""
    graph = request.app.state.graph
    vsm = request.app.state.vsm

    config = {
        "configurable": {
            "thread_id": req.session_id,
            "vsm": vsm,
        }
    }

    if req.action == "start":
        initial_state: DefectAnalysisState = {
            "company": req.company,
            "defect_description": req.defect_description,
            "product_id": req.product_id,
            "session_id": req.session_id,
            "enabled_agents": req.enabled_agents,
            "hypotheses": [],
            "selected_hypothesis": "",
            "process_history_result": None,
            "return_history_result": None,
            "test_result": None,
            "long_term_task_id": None,
            "long_term_result": None,
            "final_action_plan": "",
            "messages": [],
        }
        result = await graph.ainvoke(initial_state, config=config)

    else:
        resume_map = {
            "select_hypothesis": req.selected_hypothesis,
            "resume_long_term":  req.long_term_result,
            "chat":              req.user_message,
        }
        resume_value = resume_map.get(req.action)
        if resume_value is None:
            raise HTTPException(status_code=400, detail=f"Unknown action or missing payload: {req.action}")
        result = await graph.ainvoke(Command(resume=resume_value), config=config)

    interrupt_value = _parse_interrupt(result)

    # chat resume 후: 실제 chat 응답은 messages 마지막 AIMessage에 있음
    if req.action == "chat" and "messages" in result:
        msgs = result["messages"]
        if msgs:
            last_ai = next((m for m in reversed(msgs) if hasattr(m, "type") and m.type == "ai"), None)
            if last_ai:
                return AgentResponse(action="chat", reply=last_ai.content)

    return _build_response(interrupt_value, req.action)


@app.get("/internal/bg-status/{task_id}", response_model=BgStatusResponse, response_model_by_alias=True)
async def get_bg_status(task_id: str):
    """백그라운드 장기이력 분석 완료 상태 조회"""
    row = await get_bg_task(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return BgStatusResponse(**row)


@app.post("/internal/ingest")
async def ingest(doc_id: str, request: Request, file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        count = await ingest_document(doc_id, tmp_path, request.app.state.vsm)
        return {"doc_id": doc_id, "chunks": count}
    finally:
        os.unlink(tmp_path)


@app.delete("/internal/delete/{doc_id}")
async def delete_document(doc_id: str, request: Request):
    deleted = await request.app.state.vsm.delete_by_doc_id(doc_id)
    return {"doc_id": doc_id, "deleted_chunks": deleted}


@app.get("/internal/health")
async def health():
    return {"status": "ok"}
