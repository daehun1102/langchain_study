# Spring → FastAPI Migration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Spring Boot 백엔드를 제거하고, 그 역할(문서 CRUD + 프록시)을 ai_server(FastAPI)에 통합한다. Docker 관련 파일도 전부 제거한다.

**Architecture:** ai_server가 `/api/*` 엔드포인트를 직접 노출한다. 기존 `/internal/*` 경로를 `/api/*`로 전환하고, Spring이 처리하던 `documents` 테이블 CRUD를 sql_tools.py에 추가한다. frontend의 프록시 타겟을 `localhost:8000`으로 변경한다.

**Tech Stack:** FastAPI, SQLAlchemy (asyncpg), Python-multipart, Vue.js/Vite

**Spec:** `docs/superpowers/specs/2026-03-11-spring-to-fastapi-migration-design.md`

---

## Chunk 1: Document CRUD 함수 추가 (sql_tools.py)

**Files:**
- Modify: `ai_server/tools/sql_tools.py`
- Test: `tests/test_sql_document_tools.py`

---

- [ ] **Step 1: 테스트 파일 작성**

`tests/test_sql_document_tools.py` 를 생성한다.

```python
# tests/test_sql_document_tools.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_list_documents_returns_list():
    mock_rows = [
        {"doc_id": "abc", "filename": "a.txt", "doc_type": "txt", "status": "INDEXED", "created_at": "2026-01-01"},
    ]
    with patch("ai_server.tools.sql_tools.get_db_session") as mock_ctx:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = mock_rows
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        from ai_server.tools.sql_tools import list_documents
        result = await list_documents()
        assert result == mock_rows


@pytest.mark.asyncio
async def test_insert_document_returns_row():
    inserted = {"doc_id": "abc", "filename": "a.txt", "doc_type": "txt", "status": "INDEXED", "created_at": "2026-01-01"}
    with patch("ai_server.tools.sql_tools.get_db_session") as mock_ctx:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = inserted
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        from ai_server.tools.sql_tools import insert_document
        result = await insert_document("abc", "a.txt", "txt", "INDEXED")
        assert result["doc_id"] == "abc"
        assert result["filename"] == "a.txt"


@pytest.mark.asyncio
async def test_delete_document_executes():
    with patch("ai_server.tools.sql_tools.get_db_session") as mock_ctx:
        mock_session = AsyncMock()
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        from ai_server.tools.sql_tools import delete_document
        await delete_document("abc")
        mock_session.execute.assert_called_once()
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /c/study/langchain_study/3_playground/display_defect_chatbot
python -m pytest tests/test_sql_document_tools.py -v
```

Expected: `ImportError` 또는 `AttributeError` — 함수가 아직 없으므로 실패

- [ ] **Step 3: sql_tools.py에 document CRUD 함수 추가**

`ai_server/tools/sql_tools.py` 파일 끝에 아래를 추가한다:

```python
# ── documents 테이블 CRUD ─────────────────────────────────────

async def list_documents() -> list[dict]:
    """documents 테이블 전체 조회 (최신 순)"""
    async with get_db_session() as session:
        result = await session.execute(
            text("""
                SELECT doc_id, filename, doc_type, status, created_at
                FROM documents
                ORDER BY created_at DESC
            """)
        )
        return [dict(r) for r in result.mappings().all()]


async def insert_document(doc_id: str, filename: str, doc_type: str, status: str) -> dict:
    """documents 테이블에 행 삽입 후 삽입된 행 반환"""
    async with get_db_session() as session:
        result = await session.execute(
            text("""
                INSERT INTO documents (doc_id, filename, doc_type, status)
                VALUES (:doc_id, :filename, :doc_type, :status)
                RETURNING doc_id, filename, doc_type, status, created_at
            """),
            {"doc_id": doc_id, "filename": filename, "doc_type": doc_type, "status": status},
        )
        return dict(result.mappings().first())


async def delete_document(doc_id: str) -> None:
    """documents 테이블에서 행 삭제"""
    async with get_db_session() as session:
        await session.execute(
            text("DELETE FROM documents WHERE doc_id = :doc_id"),
            {"doc_id": doc_id},
        )
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_sql_document_tools.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 5: 커밋**

```bash
git add ai_server/tools/sql_tools.py tests/test_sql_document_tools.py
git commit -m "feat(sql_tools): add document CRUD functions (list, insert, delete)"
```

---

## Chunk 2: server.py 재편 (엔드포인트 이름 변경 + 문서 CRUD + CORS)

**Files:**
- Modify: `ai_server/server.py`

---

- [ ] **Step 1: CORS 미들웨어 import 추가**

`ai_server/server.py` 상단 import 블록에 추가:

```python
from fastapi.middleware.cors import CORSMiddleware
```

- [ ] **Step 2: app 생성 직후 CORS 미들웨어 등록**

```python
app = FastAPI(title="Defect AI Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 3: chat 엔드포인트 경로 변경**

기존:
```python
@app.post("/internal/agent", response_model=AgentResponse, response_model_by_alias=True)
async def agent_endpoint(req: AgentRequest, request: Request):
```
변경:
```python
@app.post("/api/chat/agent", response_model=AgentResponse, response_model_by_alias=True)
async def agent_endpoint(req: AgentRequest, request: Request):
```

기존:
```python
@app.get("/internal/bg-status/{task_id}", response_model=BgStatusResponse, response_model_by_alias=True)
async def get_bg_status(task_id: str):
```
변경:
```python
@app.get("/api/chat/bg-status/{task_id}", response_model=BgStatusResponse, response_model_by_alias=True)
async def get_bg_status(task_id: str):
```

- [ ] **Step 4: health 엔드포인트 경로 변경**

기존:
```python
@app.get("/internal/health")
async def health():
```
변경:
```python
@app.get("/api/health")
async def health():
```

- [ ] **Step 5: 기존 ingest/delete 엔드포인트 제거 후 문서 CRUD 엔드포인트 추가**

아래 두 기존 엔드포인트를 **제거**한다:
```python
@app.post("/internal/ingest")
async def ingest(...):
    ...

@app.delete("/internal/delete/{doc_id}")
async def delete_document(...):
    ...
```

그 자리에 아래를 추가한다:

```python
import uuid as _uuid
from ai_server.tools.sql_tools import list_documents, insert_document, delete_document as _delete_document_db


class DocumentResponse(BaseModel):
    doc_id: str
    filename: str
    doc_type: str
    status: str
    created_at: Optional[str] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


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
```

- [ ] **Step 6: 서버 기동 확인 (문법 오류 체크)**

```bash
cd /c/study/langchain_study/3_playground/display_defect_chatbot
python -c "from ai_server.server import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 7: 커밋**

```bash
git add ai_server/server.py
git commit -m "feat(server): migrate /internal/* to /api/*, add document CRUD endpoints, add CORS"
```

---

## Chunk 3: Frontend 프록시 설정 변경

**Files:**
- Modify: `frontend/vite.config.js`
- Modify: `frontend/.env.local`

---

- [ ] **Step 1: vite.config.js 프록시 기본값 변경**

`frontend/vite.config.js`:

```js
// 변경 전
const backendUrl = env.BACKEND_URL || 'http://backend:8080'
// 변경 후
const backendUrl = env.BACKEND_URL || 'http://localhost:8000'
```

- [ ] **Step 2: .env.local BACKEND_URL 변경**

`frontend/.env.local`:

```
BACKEND_URL=http://localhost:8000
```

- [ ] **Step 3: 커밋**

```bash
git add frontend/vite.config.js frontend/.env.local
git commit -m "feat(frontend): update proxy target to ai-server (localhost:8000)"
```

---

## Chunk 4: 불필요한 파일 삭제

**삭제 대상:**
- `backend/` 폴더 전체
- `docker-compose.yml`
- `ai_server/Dockerfile`
- `frontend/Dockerfile`
- `.dockerignore` (루트)
- `frontend/.dockerignore`

---

- [ ] **Step 1: backend 폴더 삭제**

```bash
cd /c/study/langchain_study/3_playground/display_defect_chatbot
rm -rf backend/
```

- [ ] **Step 2: Docker 관련 파일 삭제**

```bash
rm docker-compose.yml
rm ai_server/Dockerfile
rm frontend/Dockerfile
rm .dockerignore
rm frontend/.dockerignore
```

- [ ] **Step 3: 삭제 확인**

```bash
ls -la
ls ai_server/
ls frontend/
```

Expected: `backend/`, `docker-compose.yml`, `Dockerfile` 파일들이 없어야 함

- [ ] **Step 4: 커밋**

```bash
git add -A
git commit -m "chore: remove Spring backend and all Docker-related files"
```

---

## 완료 후 동작 확인

```bash
# ai_server 기동
uvicorn ai_server.server:app --host 0.0.0.0 --port 8000

# 다른 터미널에서 frontend 기동
cd frontend && npm run dev

# 엔드포인트 확인
curl http://localhost:8000/api/health
curl http://localhost:8000/api/documents
```
