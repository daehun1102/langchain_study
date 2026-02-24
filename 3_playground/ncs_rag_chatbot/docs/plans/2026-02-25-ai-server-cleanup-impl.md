# ai_server 루트 정리 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** ai_server 루트의 shim 6개를 삭제하고, 파이프라인 파일(loader, splitter, ingest)을 `infra/`로, 초기화 스크립트를 `scripts/`로 이동하여 루트를 깔끔하게 정리한다.

**Architecture:** shim 파일이 의존하는 `eval/tasks.py`를 실제 경로로 직접 import하도록 수정 후 shim 삭제. `loader.py`, `splitter.py`, `ingest.py`를 `infra/`로 이동하고 내부 import 경로 수정. `init_prompts.py`를 `scripts/`로 이동.

**Tech Stack:** Python 3.11, pytest, git

---

## 사전 확인

```bash
cd ai_server
pytest eval/tests/ tests/ -v
# Expected: 39 passed
```

---

## Task 1: eval/tasks.py — shim 대신 직접 import로 교체

**Files:**
- Modify: `ai_server/eval/tasks.py` (lines 18-22)

**Step 1: tasks.py import 수정**

```python
# 변경 전 (lines 18-22)
from agent import ChatAgent, PROMPT_KEYS
from embeddings import EmbeddingModel
from tool import ToolBuilder
from vector_store import VectorStoreManager
from prompt_loader import get_prompt

# 변경 후
from agents.v1.rag_agent import ChatAgent, PROMPT_KEYS
from infra.embeddings import EmbeddingModel
from tools.rag_tool import ToolBuilder
from infra.vector_store import VectorStoreManager
from infra.prompt_loader import get_prompt
```

**Step 2: 테스트 실행 — PASS 확인**

```bash
pytest eval/tests/ tests/ -v
# Expected: 39 passed
```

**Step 3: 커밋**

```bash
git add ai_server/eval/tasks.py
git commit -m "refactor(eval): tasks.py shim 대신 직접 import 경로로 교체"
```

---

## Task 2: shim 파일 6개 삭제

**Files:**
- Delete: `ai_server/agent.py`
- Delete: `ai_server/embeddings.py`
- Delete: `ai_server/tool.py`
- Delete: `ai_server/vector_store.py`
- Delete: `ai_server/prompt_loader.py`
- Delete: `ai_server/tracing.py`

**Step 1: shim 파일 삭제**

```bash
cd ai_server
git rm agent.py embeddings.py tool.py vector_store.py prompt_loader.py tracing.py
```

**Step 2: 테스트 실행 — PASS 확인**

```bash
pytest eval/tests/ tests/ -v
# Expected: 39 passed
```

**Step 3: 커밋**

```bash
git commit -m "refactor: shim 파일 6개 삭제 (agent, embeddings, tool, vector_store, prompt_loader, tracing)"
```

---

## Task 3: loader.py, splitter.py → infra/ 이동

**Files:**
- Create: `ai_server/infra/loader.py` (기존 `loader.py` 내용 그대로)
- Create: `ai_server/infra/splitter.py` (기존 `splitter.py` 내용 그대로)
- Delete: `ai_server/loader.py`
- Delete: `ai_server/splitter.py`

**Step 1: infra/loader.py 생성**

기존 `ai_server/loader.py` 내용을 그대로 복사:

```python
# ai_server/infra/loader.py
from langchain_community.document_loaders import PyPDFLoader
from langchain_upstage import UpstageDocumentParseLoader
from typing import List
from langchain_core.documents import Document


class DocumentLoader:
    """기본 PDF 파일을 로드하는 클래스 (PyPDFLoader 사용)"""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> List[Document]:
        """PDF 파일을 로드하여 문서 리스트를 반환합니다."""
        loader = PyPDFLoader(self.file_path)
        return loader.load()


class UpstageLoader:
    """Upstage Document Parse Loader를 사용하는 클래스"""

    def __init__(self, file_path: str, split: str = "page"):
        self.file_path = file_path
        self.split = split

    def load(self) -> List[Document]:
        """Upstage Loader를 사용하여 문서를 로드합니다."""
        loader = UpstageDocumentParseLoader(self.file_path, split=self.split)
        return loader.load()
```

**Step 2: infra/splitter.py 생성**

기존 `ai_server/splitter.py` 내용을 그대로 복사:

```python
# ai_server/infra/splitter.py
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List
from langchain_core.documents import Document


class DocumentSplitter:
    """문서를 청크로 분할하는 클래스"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True,
        )

    def split_documents(self, docs: List[Document]) -> List[Document]:
        """문서 리스트를 받아 청크로 분할하여 반환합니다."""
        return self.text_splitter.split_documents(docs)
```

**Step 3: 기존 파일 삭제**

```bash
cd ai_server
git rm loader.py splitter.py
```

**Step 4: 테스트 실행 — PASS 확인**

```bash
pytest eval/tests/ tests/ -v
# Expected: 39 passed
```

**Step 5: 커밋**

```bash
git add ai_server/infra/loader.py ai_server/infra/splitter.py
git commit -m "refactor(infra): loader, splitter infra/ 디렉토리로 이동"
```

---

## Task 4: ingest.py → infra/ 이동 + import 수정

**Files:**
- Create: `ai_server/infra/ingest.py` (내용 복사 + import 수정)
- Delete: `ai_server/ingest.py`
- Modify: `ai_server/server.py` (import 경로 수정)

**Step 1: infra/ingest.py 생성 (import 경로 수정)**

기존 `ingest.py` 내용을 복사하되 import 3줄 수정:

```python
# ai_server/infra/ingest.py
"""
ingest.py — PDF를 PGVector에 적재하는 모듈

변경 사항 (Phase 2):
- 메타데이터 컬럼을 doc_id + page로 단순화 (Oracle과 doc_id로 연결)
- ingest_single_document(): Spring에서 단일 PDF 처리 요청 시 호출
"""

from infra.loader import DocumentLoader        # 변경: loader → infra.loader
from infra.splitter import DocumentSplitter    # 변경: splitter → infra.splitter
from infra.embeddings import EmbeddingModel    # 변경: embeddings → infra.embeddings
from langchain_postgres import PGEngine, PGVectorStore, Column
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()

TABLE_NAME = "ncs_vectors"
VECTOR_SIZE = 1536  # text-embedding-3-small

# PGVector에는 doc_id(Oracle 참조)와 page만 저장
METADATA_COLUMNS = [
    Column("doc_id", "VARCHAR", nullable=True),
    Column("page", "INTEGER", nullable=True),
]


async def _get_pg_engine(db_connection: str):
    engine = create_async_engine(db_connection)
    return PGEngine.from_engine(engine)


async def _get_vector_store(pg_engine, embedding_model):
    return await PGVectorStore.create(
        engine=pg_engine,
        table_name=TABLE_NAME,
        embedding_service=embedding_model,
        metadata_columns=["doc_id", "page"],
    )


async def init_table(db_connection: str):
    """테이블을 초기화한다. 최초 1회 또는 스키마 변경 시 실행."""
    pg_engine = await _get_pg_engine(db_connection)
    await pg_engine.ainit_vectorstore_table(
        table_name=TABLE_NAME,
        vector_size=VECTOR_SIZE,
        metadata_columns=METADATA_COLUMNS,
        overwrite_existing=True,
    )
    print(f"[ingest] 테이블 '{TABLE_NAME}' 초기화 완료")


async def ingest_single_document(doc_id: str, file_path: str, db_connection: str) -> int:
    """단일 PDF를 PGVector에 적재한다.

    Args:
        doc_id: Oracle documents 테이블의 PK (UUID)
        file_path: PDF 파일 절대 경로
        db_connection: PGVector 연결 문자열

    Returns:
        저장된 청크 수
    """
    embedding_model = EmbeddingModel().get_embeddings()
    pg_engine = await _get_pg_engine(db_connection)
    vector_store = await _get_vector_store(pg_engine, embedding_model)

    loader = DocumentLoader(file_path=file_path)
    docs = loader.load()

    splitter = DocumentSplitter()
    splits = splitter.split_documents(docs)

    for doc in splits:
        doc.page_content = doc.page_content.replace("\x00", "")
        doc.metadata["doc_id"] = doc_id
        doc.metadata["page"] = doc.metadata.get("page", 0)

    await vector_store.aadd_documents(splits)
    print(f"[ingest] doc_id={doc_id}, 청크={len(splits)}개 저장 완료")
    return len(splits)


if __name__ == "__main__":
    import sys
    db = os.getenv("DB_CONNECTION", "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db")

    if len(sys.argv) == 2 and sys.argv[1] == "init":
        asyncio.run(init_table(db))
    elif len(sys.argv) == 3:
        asyncio.run(ingest_single_document(sys.argv[1], sys.argv[2], db))
    else:
        print("Usage:")
        print("  python -m infra.ingest init               # 테이블 초기화")
        print("  python -m infra.ingest <doc_id> <path>    # 단일 파일 적재")
```

**Step 2: 기존 ingest.py 삭제**

```bash
cd ai_server
git rm ingest.py
```

**Step 3: server.py import 수정**

`ai_server/server.py`에서:

```python
# 변경 전
from ingest import ingest_single_document

# 변경 후
from infra.ingest import ingest_single_document
```

**Step 4: 테스트 실행 — PASS 확인**

```bash
pytest eval/tests/ tests/ -v
# Expected: 39 passed
```

**Step 5: server.py import 오류 없음 확인**

```bash
python -c "import server; print('OK')"
# Expected: OK  (또는 dotenv/DB 관련 경고는 무시)
```

**Step 6: 커밋**

```bash
git add ai_server/infra/ingest.py ai_server/server.py
git commit -m "refactor(infra): ingest.py infra/ 이동 + import 경로 수정"
```

---

## Task 5: init_prompts.py → scripts/ 이동

**Files:**
- Create: `ai_server/scripts/__init__.py`
- Create: `ai_server/scripts/init_prompts.py` (내용 그대로)
- Delete: `ai_server/init_prompts.py`

**Step 1: scripts/ 디렉토리 + __init__.py 생성**

```python
# ai_server/scripts/__init__.py
# (빈 파일)
```

**Step 2: scripts/init_prompts.py 생성**

기존 `init_prompts.py` 내용 그대로 복사. 단, `REDIS_HOST/PORT`를 config에서 읽도록 수정:

```python
# ai_server/scripts/init_prompts.py
"""
init_prompts.py — Redis에 초기 프롬프트 데이터를 등록하는 스크립트

실행: python -m scripts.init_prompts
Redis가 실행 중이어야 합니다.
"""

import redis
from config import settings

PREFIX = "prompt:"

PROMPTS = {
    "agent_system_prompt": (
        "너는 NCS(국가직무능력표준) 문서에서 정보를 검색하여 답변해주는 친절한 AI 어시스턴트야.\n"
        "사용자의 질의에 항상 retrieve_context 도구를 사용해서 먼저 관련 문서를 검색하고 답변해줘.\n"
        "문서에서 찾은 내용만 답변하고, 모르는 내용은 추측하지 마."
    ),
    "answer_format_prompt": (
        "답변 형식 지침:\n"
        "- 마크다운 형식으로 작성해줘 (헤딩, 목록, 굵게 등 적극 활용)\n"
        "- 답변 말미에 출처를 명시해줘: '출처: 페이지 {페이지번호}'\n"
        "- 여러 문서에서 정보를 가져왔다면 각 내용의 출처를 구분해서 표시해줘\n"
        "- 불확실한 내용은 반드시 '문서에서 확인되지 않음'이라고 표시해줘"
    ),
    "no_document_prompt": (
        "관련 문서를 찾지 못했을 때 안내:\n"
        "retrieve_context 도구로 검색했으나 관련 내용을 찾지 못한 경우, 다음과 같이 안내해줘:\n"
        "'해당 카테고리에 등록된 문서에서 관련 내용을 찾을 수 없습니다. "
        "다른 카테고리를 선택하거나, 질문을 좀 더 구체적으로 바꿔보세요.'"
    ),
    "query_enhance_prompt": (
        "검색 쿼리 최적화 지침:\n"
        "- 사용자 질의가 짧거나 모호하면 NCS 문서 맥락에 맞게 구체화하여 검색해줘\n"
        "- 예: '테스트란?' → 'NCS IT테스트 기획 및 설계 방법'\n"
        "- 첫 검색 결과가 불충분하면 다른 키워드로 재검색해줘 (최대 2회)\n"
        "- 검색어는 한국어로 작성해줘"
    ),
    "category_hint_prompt": (
        "카테고리 안내:\n"
        "카테고리가 선택되지 않아 전체 문서에서 검색합니다.\n"
        "답변 말미에 다음 문구를 추가해줘:\n"
        "'💡 좌측 카테고리 필터를 선택하면 특정 분야의 문서만 검색하여 더 정확한 답변을 받을 수 있습니다.'"
    ),
}

if __name__ == "__main__":
    r = redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)
    try:
        r.ping()
    except redis.ConnectionError:
        print(f"[ERROR] Redis에 연결할 수 없습니다: {settings.redis_host}:{settings.redis_port}")
        raise SystemExit(1)

    for key, value in PROMPTS.items():
        r.set(PREFIX + key, value)
        print(f"[init_prompts] 저장 완료: {PREFIX + key}")

    print(f"\n총 {len(PROMPTS)}개 프롬프트 등록 완료")
    print("확인: redis-cli keys 'prompt:*'")
```

**Step 3: 기존 파일 삭제**

```bash
cd ai_server
git rm init_prompts.py
```

**Step 4: 테스트 실행 — PASS 확인**

```bash
pytest eval/tests/ tests/ -v
# Expected: 39 passed
```

**Step 5: 커밋**

```bash
git add ai_server/scripts/
git commit -m "refactor(scripts): init_prompts.py scripts/ 디렉토리로 이동, config 연동"
```

---

## Task 6: infra/__init__.py — loader, splitter, ingest export 추가

**Files:**
- Modify: `ai_server/infra/__init__.py`

**Step 1: __init__.py 업데이트**

```python
# ai_server/infra/__init__.py
from infra.embeddings import EmbeddingModel
from infra.vector_store import VectorStoreManager
from infra.prompt_loader import get_prompt
from infra.tracing import setup_tracing
from infra.loader import DocumentLoader
from infra.splitter import DocumentSplitter
from infra.ingest import ingest_single_document

__all__ = [
    "EmbeddingModel",
    "VectorStoreManager",
    "get_prompt",
    "setup_tracing",
    "DocumentLoader",
    "DocumentSplitter",
    "ingest_single_document",
]
```

**Step 2: 전체 테스트 최종 확인**

```bash
pytest eval/tests/ tests/ -v
# Expected: 39 passed
```

**Step 3: 서버 import 확인**

```bash
python -c "from infra import EmbeddingModel, VectorStoreManager, ingest_single_document; print('OK')"
# Expected: OK
```

**Step 4: 최종 커밋**

```bash
git add ai_server/infra/__init__.py
git commit -m "refactor(infra): __init__.py에 loader, splitter, ingest export 추가"
```

---

## 최종 확인

```bash
# 루트 파일 목록 확인 (server.py, config.py, pytest.ini, requirements.txt만 남아야 함)
ls ai_server/*.py

# Expected:
# ai_server/config.py
# ai_server/server.py

# 전체 테스트
pytest eval/tests/ tests/ -v
# Expected: 39 passed
```
