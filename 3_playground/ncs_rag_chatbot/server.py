"""
server.py — Python FastAPI AI 서버 (내부 전용)

외부 공개 API(/api/*)는 Spring Boot(8080)가 담당한다.
이 서버는 Spring에서만 호출하는 내부 엔드포인트만 제공한다.

엔드포인트:
  GET  /internal/health  — 헬스 체크
  POST /internal/ingest  — PDF 벡터 저장 (Spring 호출)
  POST /internal/chat    — RAG 채팅 (Spring 호출)

실행: uvicorn server:app --reload --port 8000
"""

import sys
import os
import logging
import traceback
from contextlib import asynccontextmanager
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# 트레이싱은 LangChain import보다 먼저 초기화해야 모든 호출을 계측한다
from tracing import setup_tracing
setup_tracing()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from embeddings import EmbeddingModel
from vector_store import VectorStoreManager
from agent import ChatAgent
from tool import ToolBuilder
from ingest import ingest_single_document

logger = logging.getLogger("ncs_server")

DB_CONNECTION = os.getenv(
    "DB_CONNECTION",
    "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db"
)

vector_store_manager: Optional[VectorStoreManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 권장 방식의 startup/shutdown 관리."""
    global vector_store_manager
    emb = EmbeddingModel().get_embeddings()
    vector_store_manager = await VectorStoreManager.create(DB_CONNECTION, emb)
    logger.info("[server] VectorStoreManager 초기화 완료")
    yield
    # shutdown 정리 작업 (필요 시 추가)


app = FastAPI(title="NCS RAG AI Server (Internal)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ── Request / Response 모델 ───────────────────────────────────

class IngestRequest(BaseModel):
    doc_id: str
    file_path: str


class IngestResponse(BaseModel):
    doc_id: str
    chunks: int
    status: str


class ChatRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None


class SourceInfo(BaseModel):
    content: str
    doc_id: str
    page: int


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]


class DeleteResponse(BaseModel):
    doc_id: str
    deleted_chunks: int


# ── Endpoints ─────────────────────────────────────────────────

@app.get("/internal/health")
async def health():
    return {"status": "ok"}


@app.delete("/internal/delete/{doc_id}", response_model=DeleteResponse)
async def delete_vectors(doc_id: str):
    """Spring에서 문서 삭제 시 호출. PGVector에서 해당 doc_id의 모든 청크를 삭제한다."""
    try:
        deleted_count = await vector_store_manager.delete_by_doc_id(doc_id)
        logger.info("[delete] 벡터 삭제 완료: doc_id=%s, chunks=%d", doc_id, deleted_count)
        return DeleteResponse(doc_id=doc_id, deleted_chunks=deleted_count)
    except Exception:
        logger.error("[delete] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"벡터 삭제 실패: doc_id={doc_id}")


@app.post("/internal/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    """Spring에서 PDF 업로드 후 호출. PGVector에 벡터 저장."""
    try:
        chunks = await ingest_single_document(req.doc_id, req.file_path, DB_CONNECTION)
        return IngestResponse(doc_id=req.doc_id, chunks=chunks, status="INDEXED")
    except Exception:
        logger.error("[ingest] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"ingest 실패: doc_id={req.doc_id}")


@app.post("/internal/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Spring에서 호출. doc_ids 범위 내 RAG 검색 후 AI 응답 생성."""
    doc_ids = req.doc_ids or []

    tool_builder = ToolBuilder(vector_store_manager)
    tools = tool_builder.build_tools(doc_ids=doc_ids)

    agent = ChatAgent()
    agent.create_agent(tools)

    last_message = await agent.run(req.query)
    answer = last_message.content if last_message else "응답을 생성할 수 없습니다."

    sources = await _collect_sources(req.query, doc_ids)

    return ChatResponse(answer=answer, sources=sources)


async def _collect_sources(query: str, doc_ids: List[str]) -> List[SourceInfo]:
    """벡터 스토어에서 직접 유사 문서를 검색하여 sources를 반환한다.

    content_and_artifact 도구를 ainvoke()로 직접 호출하면 content(str)만
    반환되므로, vector_store_manager를 직접 호출한다.
    """
    try:
        retrieved_docs = await vector_store_manager.similarity_search_by_doc_ids(
            query, doc_ids=doc_ids, k=4
        )
        return [
            SourceInfo(
                content=doc.page_content[:300],
                doc_id=doc.metadata.get("doc_id", ""),
                page=doc.metadata.get("page", 0),
            )
            for doc in retrieved_docs
        ]
    except Exception:
        logger.warning("[sources] 소스 추출 실패:\n%s", traceback.format_exc())
        return []
