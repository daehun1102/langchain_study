"""
server.py — Python FastAPI AI 서버 (내부 전용)

엔드포인트:
  POST /internal/ingest  — Spring에서 PDF 업로드 후 벡터 저장 요청
  POST /internal/chat    — Spring에서 채팅 요청 (doc_ids 포함)
  GET  /internal/health  — 헬스 체크

외부(프론트엔드)에서 직접 호출하지 않는다. Spring Boot(8080)만 이 서버를 호출한다.
실행: uvicorn server:app --reload --port 8000
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

from embeddings import EmbeddingModel
from vector_store import VectorStoreManager
from agent import ChatAgent
from tool import ToolBuilder
from ingest import ingest_single_document

app = FastAPI(title="NCS RAG AI Server (Internal)")

# Spring Boot에서만 호출 — CORS를 Spring 서버로 제한
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

DB_CONNECTION = os.getenv(
    "DB_CONNECTION",
    "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db"
)

vector_store_manager: Optional[VectorStoreManager] = None


@app.on_event("startup")
async def startup():
    global vector_store_manager
    emb = EmbeddingModel().get_embeddings()
    vector_store_manager = await VectorStoreManager.create(DB_CONNECTION, emb)
    print("[server] VectorStoreManager 초기화 완료")


# ── Request / Response 모델 ──────────────────────────────────

class IngestRequest(BaseModel):
    doc_id: str     # Oracle에서 발급한 UUID
    file_path: str  # PDF 파일 절대 경로 (Spring과 공유된 로컬 경로)


class IngestResponse(BaseModel):
    doc_id: str
    chunks: int
    status: str     # INDEXED | FAILED


class ChatRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None  # Oracle에서 조회한 doc_id 목록


class SourceInfo(BaseModel):
    content: str
    doc_id: str
    page: int


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]


# ── Endpoints ────────────────────────────────────────────────

@app.get("/internal/health")
async def health():
    return {"status": "ok"}


@app.post("/internal/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    """Spring에서 PDF 업로드 후 호출. doc_id와 파일 경로를 받아 PGVector에 벡터 저장."""
    try:
        chunks = await ingest_single_document(req.doc_id, req.file_path, DB_CONNECTION)
        return IngestResponse(doc_id=req.doc_id, chunks=chunks, status="INDEXED")
    except Exception as e:
        print(f"[ingest] 오류: {e}")
        return IngestResponse(doc_id=req.doc_id, chunks=0, status="FAILED")


@app.post("/internal/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Spring에서 호출. doc_ids 범위 내에서 RAG 검색 후 AI 응답 생성."""
    doc_ids = req.doc_ids or []

    tool_builder = ToolBuilder(vector_store_manager)
    tools = tool_builder.build_tools(doc_ids=doc_ids)

    agent = ChatAgent()
    agent.create_agent(tools)

    last_message = await agent.run(req.query)
    answer = last_message.content if last_message else "응답을 생성할 수 없습니다."

    # sources 추출 (tool 호출 결과에서)
    sources = []

    return ChatResponse(answer=answer, sources=sources)
