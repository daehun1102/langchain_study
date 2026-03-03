# display_defect_chatbot/ai_server/server.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
import os
import tempfile

from ai_server.config import get_settings
from ai_server.infra.vector_store import VectorStoreManager
from ai_server.infra.ingest import ingest_document
from ai_server.infra.tracing import setup_tracing
from ai_server.infra.database import get_db_session
from ai_server.agents.main_agent import run_main_analysis
from ai_server.agents.graph import investigation_graph, DefectAnalysisState
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import text

settings = get_settings()
app = FastAPI(title="Defect AI Server")

vsm: Optional[VectorStoreManager] = None


@app.on_event("startup")
async def startup():
    global vsm
    setup_tracing(settings.phoenix_collector_endpoint)
    embedding = OpenAIEmbeddings(model=settings.embedding_model)
    vsm = await VectorStoreManager.create(settings.pg_async_url, embedding)


# ── Request/Response Models ──────────────────────────────────

class AnalyzeRequest(BaseModel):
    session_id: str
    company: str
    defect_description: str


class AnalyzeResponse(BaseModel):
    session_id: str
    hypotheses: list[str]


class InvestigateRequest(BaseModel):
    session_id: str
    company: str
    defect_description: str
    product_id: str
    selected_hypothesis: str


class InvestigateResponse(BaseModel):
    action_plan: str
    process_history: list
    return_history: list
    test_results: list
    long_term_task_id: Optional[str]


class BgStatusResponse(BaseModel):
    task_id: str
    status: str
    result_text: Optional[str]


# ── Endpoints ──────────────────────────────────────────────

@app.post("/internal/analyze", response_model=AnalyzeResponse)
async def analyze_defect(req: AnalyzeRequest):
    """1단계: RAG로 불량 원인 가설 생성"""
    hypotheses = await run_main_analysis(req.defect_description, req.company, vsm)
    return AnalyzeResponse(session_id=req.session_id, hypotheses=hypotheses)


@app.post("/internal/investigate", response_model=InvestigateResponse)
async def investigate_defect(req: InvestigateRequest):
    """2단계: 가설 선택 후 Send API 병렬 서브에이전트 실행"""
    config = {"configurable": {"thread_id": req.session_id}}
    initial_state: DefectAnalysisState = {
        "company": req.company,
        "defect_description": req.defect_description,
        "product_id": req.product_id,
        "selected_hypothesis": req.selected_hypothesis,
        "session_id": req.session_id,
        "process_history_result": [],
        "return_history_result": [],
        "test_result": [],
        "long_term_task_id": [],
        "final_action_plan": "",
    }
    state = await investigation_graph.ainvoke(initial_state, config=config)

    task_ids = state.get("long_term_task_id", [])
    return InvestigateResponse(
        action_plan=state.get("final_action_plan", ""),
        process_history=state.get("process_history_result", []),
        return_history=state.get("return_history_result", []),
        test_results=state.get("test_result", []),
        long_term_task_id=task_ids[0] if task_ids else None,
    )


@app.get("/internal/bg-status/{task_id}", response_model=BgStatusResponse)
async def get_bg_status(task_id: str):
    """백그라운드 장기이력 분석 완료 상태 조회"""
    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT task_id, status, result_text FROM background_tasks WHERE task_id = :tid"),
            {"tid": task_id},
        )
        row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return BgStatusResponse(**dict(row))


@app.post("/internal/ingest")
async def ingest(doc_id: str, file: UploadFile = File(...)):
    """txt 문서를 PGVector에 색인"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        count = await ingest_document(doc_id, tmp_path, vsm)
        return {"doc_id": doc_id, "chunks": count}
    finally:
        os.unlink(tmp_path)


@app.delete("/internal/delete/{doc_id}")
async def delete_document(doc_id: str):
    deleted = await vsm.delete_by_doc_id(doc_id)
    return {"doc_id": doc_id, "deleted_chunks": deleted}


@app.get("/internal/health")
async def health():
    return {"status": "ok"}
