import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from embeddings import EmbeddingModel
from vector_store import VectorStoreManager
from langchain.chat_models import init_chat_model

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store = None
llm = None

DB_CONNECTION = "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db"
TABLE_NAME = "test_table_filtered"

CATEGORIES = {
    "정보기술개발": ["SW아키텍쳐", "응용SW엔지니어링", "임베디드SW엔지니어링"],
    "정보기술관리": ["IT테스트", "IT품질보증", "IT프로젝트관리"],
    "직업기초능력": ["문제해결능력", "수리능력", "의사소통능력"],
}


class ChatRequest(BaseModel):
    query: str
    main_category: Optional[str] = None
    sub_category: Optional[str] = None


@app.on_event("startup")
async def startup():
    global store, llm
    emb = EmbeddingModel().get_embeddings()
    mgr = await VectorStoreManager.create(
        connection_string=DB_CONNECTION,
        table_name=TABLE_NAME,
        embedding_model=emb,
        metadata_columns=["main_category", "sub_category", "source", "page"],
    )
    store = mgr.get_vector_store()
    llm = init_chat_model("gpt-4o-mini")


@app.get("/api/categories")
async def categories():
    return CATEGORIES


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    filt = {}
    if req.main_category:
        filt["main_category"] = {"$eq": req.main_category}
    if req.sub_category:
        filt["sub_category"] = {"$eq": req.sub_category}

    if filt:
        docs = await store.asimilarity_search(req.query, k=4, filter=filt)
    else:
        docs = await store.asimilarity_search(req.query, k=4)

    ctx = "\n\n---\n\n".join(d.page_content for d in docs)

    sources = []
    for d in docs:
        m = d.metadata
        sources.append({
            "content": d.page_content[:300],
            "main_category": m.get("main_category", ""),
            "sub_category": m.get("sub_category", ""),
            "source": m.get("source", ""),
            "page": m.get("page", 0),
        })

    msgs = [
        {
            "role": "system",
            "content": (
                "너는 NCS(국가직무능력표준) 문서 전문가야. "
                "다음 참고 문서를 바탕으로 정확하고 친절하게 답변해줘. "
                "답변에 관련 내용의 출처(파일명, 페이지)를 언급해줘.\n\n"
                f"{ctx}"
            ),
        },
        {"role": "user", "content": req.query},
    ]
    resp = await llm.ainvoke(msgs)

    return {
        "answer": resp.content,
        "sources": sources,
        "filter": filt if filt else None,
    }


# Serve frontend static files
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
