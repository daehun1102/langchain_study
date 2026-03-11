# Spring → FastAPI 이관 설계

**날짜:** 2026-03-11
**목표:** Spring Boot 백엔드를 제거하고, 그 역할을 ai_server(FastAPI)로 통합한다.
Docker 관련 파일 전부 제거. 최종 구성은 `ai_server`, `frontend` 두 폴더만 남는다.

---

## 배경

Spring 백엔드는 순수 프록시 + 문서 CRUD 역할만 한다.
ai_server는 이미 PostgreSQL(SQLAlchemy)에 직접 연결되어 있으므로, Spring 없이 모든 역할을 직접 수행할 수 있다.

---

## 변경 범위

### 1. ai_server/server.py

**엔드포인트 재편 (`/internal/*` → `/api/*`)**

| 변경 전 | 변경 후 | 비고 |
|---|---|---|
| `POST /internal/agent` | `POST /api/chat/agent` | 동일 로직 |
| `GET /internal/bg-status/{id}` | `GET /api/chat/bg-status/{id}` | 동일 로직 |
| `POST /internal/ingest?doc_id=...` | `POST /api/documents` | doc_id 서버 자동 생성 + ingest + DB insert |
| `DELETE /internal/delete/{id}` | `DELETE /api/documents/{id}` | vector 삭제 + DB delete |
| *(없음)* | `GET /api/documents` | documents 테이블 조회 |
| `GET /internal/health` | `GET /api/health` | 동일 로직 |

**Spring `SessionController` (`/api/sessions/bg-status/{id}`) 처리:**
프론트엔드는 `/api/chat/bg-status/{id}`만 사용한다. 중복 경로이므로 이관 후 의도적으로 제거.

**`POST /api/documents` 상세:**
- `doc_id`: query param 제거, 서버에서 `uuid.uuid4()`로 자동 생성
- multipart `file` (UploadFile) 수신
- `ingest_document(doc_id, tmp_path, vsm)` 호출 후 documents 테이블 insert
- 응답: `{"doc_id": str, "filename": str, "doc_type": str, "status": str, "created_at": str}`

**CORS 추가:**
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
```

### 2. ai_server/tools/sql_tools.py

문서 CRUD 함수 3개 추가:
- `list_documents()` → `SELECT doc_id, filename, doc_type, status, created_at FROM documents ORDER BY created_at DESC`
- `insert_document(doc_id, filename, doc_type, status)` → `INSERT INTO documents` 후 삽입된 행 반환
- `delete_document(doc_id)` → `DELETE FROM documents WHERE doc_id = :doc_id`

### 3. frontend/vite.config.js

```js
// 변경 전
const backendUrl = env.BACKEND_URL || 'http://backend:8080'
// 변경 후
const backendUrl = env.BACKEND_URL || 'http://localhost:8000'
```

### 4. frontend/.env.local

```
# 변경 전
BACKEND_URL=http://localhost:8080
# 변경 후
BACKEND_URL=http://localhost:8000
```

### 5. 삭제할 파일/폴더

| 대상 | 이유 |
|---|---|
| `backend/` 폴더 전체 | Spring 프로젝트 제거 |
| `docker-compose.yml` | Docker 제거 |
| `ai_server/Dockerfile` | Docker 제거 |
| `frontend/Dockerfile` | Docker 제거 |
| `.dockerignore` (루트) | Docker 제거 |
| `frontend/.dockerignore` | Docker 제거 |

---

## 최종 구조

```
display_defect_chatbot/
├── ai_server/          # FastAPI — AI + 문서 관리 + 모든 /api/* 엔드포인트
├── frontend/           # Vue.js — /api/* 를 ai-server(localhost:8000)로 프록시
├── db/
│   └── init.sql        # PostgreSQL 초기화 스크립트
└── .env.example
```

## 실행 방법 (git clone 후)

```bash
# 1. PostgreSQL 실행 후 DB 초기화
psql -U postgres -d defect_db -f db/init.sql

# 2. 환경변수 설정
cp .env.example .env
# .env에 OPENAI_API_KEY 입력

# 3. ai_server 실행
pip install -r ai_server/requirements.txt
uvicorn ai_server.server:app --host 0.0.0.0 --port 8000

# 4. frontend 실행
cd frontend
npm install
npm run dev
```

---

## 영향 없는 항목

- `frontend/src/api/defectApi.js` — `/api/*` 경로 그대로 사용, 변경 불필요
- `db/init.sql` — 변경 없음
- `.env.example` — 변경 불필요
- ai_server 내부 로직(agents, tools/rag_tool, infra) — 변경 없음
