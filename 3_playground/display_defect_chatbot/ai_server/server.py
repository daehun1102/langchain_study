# ai_server/server.py
from contextlib import asynccontextmanager
from typing import Optional
import logging

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import OpenAIEmbeddings
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel
import os
import tempfile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from ai_server.agents.graph import build_investigation_graph, ALL_AGENTS, DefectAnalysisState
from ai_server.config import get_settings
from ai_server.infra.checkpointer import checkpointer_lifespan
from ai_server.infra.ingest import ingest_document
from ai_server.infra.vector_store import VectorStoreManager
from ai_server.tools.sql_tools import get_bg_task, list_documents, insert_document, delete_document as _delete_document_db
import uuid as _uuid

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    embedding = OpenAIEmbeddings(model=settings.embedding_model)
    app.state.vsm = await VectorStoreManager.create(settings.pg_async_url, embedding)
    async with checkpointer_lifespan(settings.pg_checkpoint_url) as checkpointer:
        app.state.checkpointer = checkpointer
        app.state.graph = build_investigation_graph(checkpointer)
        yield


app = FastAPI(title="Defect AI Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    notify_email: Optional[str] = None

    @field_validator("company", "defect_description", "product_id", mode="before")
    @classmethod
    def null_to_empty_string(cls, v: object) -> str:
        return v if v is not None else ""

    @field_validator("enabled_agents", mode="before")
    @classmethod
    def null_to_default_agents(cls, v: object) -> list:
        return v if v is not None else list(ALL_AGENTS)


class AgentResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    action: str
    # start — each item: {"text": str, "recommended_agents": list[str]}
    hypotheses: Optional[list[dict]] = None
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

@app.post("/api/chat/agent", response_model=AgentResponse, response_model_by_alias=True)
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
            "notify_email": None,
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
        if req.action == "select_hypothesis":
            # enabled_agents를 함께 전달해 그래프 state 업데이트
            resume_value = {
                "selected_hypothesis": req.selected_hypothesis,
                "enabled_agents": req.enabled_agents,
                "notify_email": req.notify_email,
            }
        elif req.action == "resume_long_term":
            resume_value = req.long_term_result
        elif req.action == "chat":
            resume_value = req.user_message
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")
        if resume_value is None:
            raise HTTPException(status_code=400, detail=f"Missing payload for action: {req.action}")
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


@app.get("/api/chat/bg-status/{task_id}", response_model=BgStatusResponse, response_model_by_alias=True)
async def get_bg_status(task_id: str):
    """백그라운드 장기이력 분석 완료 상태 조회"""
    row = await get_bg_task(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return BgStatusResponse(**row)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    doc_id: str
    filename: str
    doc_type: str
    status: str
    created_at: Optional[str] = None


@app.get("/api/documents", response_model=list[DocumentResponse])
async def get_documents():
    rows = await list_documents()
    return [
        DocumentResponse(
            doc_id=r["doc_id"],
            filename=r["filename"],
            doc_type=r["doc_type"],
            status=r["status"],
            created_at=str(r["created_at"]) if r["created_at"] else None,
        )
        for r in rows
    ]


@app.post("/api/documents", response_model=DocumentResponse)
async def upload_document(request: Request, file: UploadFile = File(...)):
    doc_id = str(_uuid.uuid4())
    vsm = request.app.state.vsm

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        await ingest_document(doc_id, tmp_path, vsm)
    finally:
        os.unlink(tmp_path)

    row = await insert_document(doc_id, file.filename, "txt", "INDEXED")
    return DocumentResponse(
        doc_id=row["doc_id"],
        filename=row["filename"],
        doc_type=row["doc_type"],
        status=row["status"],
        created_at=str(row["created_at"]) if row["created_at"] else None,
    )


@app.delete("/api/documents/{doc_id}")
async def delete_doc(doc_id: str, request: Request):
    vsm = request.app.state.vsm
    await vsm.delete_by_doc_id(doc_id)
    await _delete_document_db(doc_id)
    return {"doc_id": doc_id}


@app.get("/api/health")
async def health():
    return {"status": "ok"}
