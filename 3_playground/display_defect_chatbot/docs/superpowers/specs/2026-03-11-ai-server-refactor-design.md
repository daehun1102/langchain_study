# ai_server 폴더 구조 리팩토링 설계

**날짜:** 2026-03-11
**대상:** `ai_server/` (FastAPI + LangGraph)
**목표:** 유지보수성, 명확성, 클린 아키텍처 방향성 확보

---

## 1. 배경 및 문제점

현재 `ai_server/`는 다음 문제를 갖고 있다.

- **`server.py` God File**: FastAPI 앱 팩토리, lifespan, Request/Response 스키마, 헬퍼 함수, 엔드포인트 핸들러 4개가 273줄 단일 파일에 혼재.
- **`tools/sql_tools.py` 혼합 책임**: 서브에이전트용 DB 쿼리(도메인)와 문서/백그라운드 태스크 CRUD(인프라)가 한 파일에 공존.
- **레이어 경계 부재**: API 핸들러가 `request.app.state`를 통해 인프라 객체를 직접 참조하고, 비즈니스 로직(interrupt 파싱, 응답 조립)을 직접 포함.

---

## 2. 목표 구조

```
ai_server/
├── server.py                    ← 앱 팩토리 + lifespan + CORS (~40줄)
├── config.py                    ← 설정 (변경 없음)
│
├── api/                         ← Interface Adapters
│   ├── __init__.py
│   ├── schemas.py               ← Request/Response Pydantic 모델
│   ├── deps.py                  ← FastAPI Depends (get_graph, get_vsm)
│   ├── chat.py                  ← /api/chat/* 라우터
│   └── documents.py             ← /api/documents/* 라우터
│
├── services/                    ← Application Layer
│   ├── __init__.py
│   ├── agent_service.py         ← 그래프 invoke, interrupt 파싱, 응답 조립
│   └── document_service.py      ← 문서 업로드/삭제 조율 (ingest + repo)
│
├── agents/                      ← Domain Layer (변경 없음)
│   ├── __init__.py
│   ├── graph.py
│   ├── state.py
│   ├── prompts.py
│   ├── synthesis_node.py
│   └── sub/
│       ├── process_history.py
│       ├── return_history.py
│       ├── test_result.py
│       └── long_term.py
│
├── tools/                       ← LangChain 도구
│   ├── __init__.py
│   └── rag_tool.py              ← (변경 없음)
│
├── repositories/                ← Data Access Layer
│   ├── __init__.py
│   ├── agent_queries.py         ← query_process/return/test/long_term_history
│   ├── document_repo.py         ← list/insert/delete_document
│   └── bg_task_repo.py          ← insert/complete/fail/get_bg_task
│
└── infra/                       ← Infrastructure (변경 없음)
    ├── __init__.py
    ├── database.py
    ├── vector_store.py
    ├── ingest.py
    ├── checkpointer.py
    ├── graph_logger.py
    └── email_utils.py
```

---

## 3. 레이어 책임 및 의존 방향

### 의존 방향 (단방향)

```
api/ → services/ → agents/ + repositories/ + infra/
agents/ → repositories/ + tools/
tools/ → infra/
```

- `api/`는 `services/`만 호출. `agents/`, `infra/`를 직접 참조하지 않음.
- `services/`는 도메인(`agents/`), 데이터 접근(`repositories/`), 인프라(`infra/`) 조율.
- `agents/`는 `repositories/`(쿼리), `tools/`(RAG) 사용. `api/`, `services/`를 모름.

### 각 레이어 책임

| 레이어 | 폴더 | 책임 |
|---|---|---|
| Interface Adapters | `api/` | HTTP 파싱/직렬화, 의존성 주입, 라우팅 |
| Application | `services/` | 비즈니스 로직 조율, 유스케이스 실행 |
| Domain | `agents/` | LangGraph 그래프, 노드, 상태, 프롬프트 |
| Data Access | `repositories/` | SQL 실행, DB 접근 |
| Infrastructure | `infra/` | DB 엔진, 벡터 스토어, 체크포인터, 유틸리티 |

---

## 4. 마이그레이션 상세

### 4-1. `server.py` 분해

**이동 내용:**

| 현재 위치 | 이동 후 |
|---|---|
| `AgentRequest`, `AgentResponse`, `BgStatusResponse`, `DocumentResponse` | `api/schemas.py` |
| `_parse_interrupt()`, `_build_response()` | `services/agent_service.py` |
| `/api/chat/agent`, `/api/chat/bg-status/{task_id}` 핸들러 | `api/chat.py` |
| `/api/documents` CRUD 핸들러 | `api/documents.py` |
| `lifespan`, `app = FastAPI(...)`, CORS 미들웨어 | `server.py` (유지) |

**리팩토링 후 `server.py` (~40줄):**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import OpenAIEmbeddings

from ai_server.api.chat import router as chat_router
from ai_server.api.documents import router as documents_router
from ai_server.agents.graph import build_investigation_graph
from ai_server.config import get_settings
from ai_server.infra.checkpointer import checkpointer_lifespan
from ai_server.infra.vector_store import VectorStoreManager

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
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(chat_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
```

### 4-2. `api/deps.py` — 의존성 주입

```python
from fastapi import Request

def get_graph(request: Request):
    return request.app.state.graph

def get_vsm(request: Request):
    return request.app.state.vsm
```

라우터에서 `request.app.state.graph` 직접 접근 제거. `Depends(get_graph)` 패턴 사용.

### 4-3. `services/agent_service.py`

현재 `server.py`의 `_parse_interrupt()`, `_build_response()`, action별 분기 로직을 이동.

```python
async def handle_agent_request(req, graph, vsm) -> AgentResponse:
    # config 구성, action 분기, graph.ainvoke(), interrupt 파싱, 응답 조립
    ...
```

### 4-4. `services/document_service.py`

현재 `server.py`의 업로드/삭제 핸들러 로직(ingest + repo 조율, rollback)을 이동.

```python
async def upload_document(doc_id, tmp_path, filename, vsm) -> dict:
    await ingest_document(doc_id, tmp_path, vsm)
    try:
        return await document_repo.insert(doc_id, filename, "txt", "INDEXED")
    except Exception:
        await vsm.delete_by_doc_id(doc_id)  # rollback
        raise
```

### 4-5. `tools/sql_tools.py` → `repositories/` 분리

| 함수 | 이동 위치 |
|---|---|
| `query_process_history`, `query_return_history`, `query_test_results`, `query_long_term_history` | `repositories/agent_queries.py` |
| `list_documents`, `insert_document`, `delete_document` | `repositories/document_repo.py` |
| `insert_bg_task`, `complete_bg_task`, `fail_bg_task`, `get_bg_task` | `repositories/bg_task_repo.py` |

`tools/sql_tools.py` 파일은 삭제.

### 4-6. 서브에이전트 import 변경

`agents/sub/` 4개 파일 모두:
```python
# 변경 전
from ai_server.tools.sql_tools import query_process_history

# 변경 후
from ai_server.repositories.agent_queries import query_process_history
```

---

## 5. 변경 범위 요약

| 파일/폴더 | 변경 유형 |
|---|---|
| `server.py` | 대폭 축소 (리팩토링) |
| `api/` | 신규 생성 (schemas, deps, chat, documents) |
| `services/` | 신규 생성 (agent_service, document_service) |
| `repositories/` | 신규 생성 (agent_queries, document_repo, bg_task_repo) |
| `tools/sql_tools.py` | 삭제 |
| `agents/sub/*.py` | import 경로 수정만 |
| `agents/`, `tools/rag_tool.py`, `infra/`, `config.py` | 변경 없음 |

---

## 6. 성공 기준

- `server.py`가 앱 팩토리와 lifespan만 포함 (~40줄)
- 각 라우터 파일이 HTTP 변환과 service 호출만 담당
- `repositories/` 각 파일이 단일 도메인의 SQL만 포함
- 기존 API 동작이 그대로 유지됨 (엔드포인트 경로, 요청/응답 형식 불변)
- `from ai_server.tools.sql_tools` import가 코드베이스에서 완전히 제거됨
