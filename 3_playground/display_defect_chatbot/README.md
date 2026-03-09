# Display Defect Chatbot

디스플레이 패널 픽셀 불량을 AI로 분석하는 챗봇 시스템입니다.
불량 설명을 입력하면 RAG 기반 가설을 생성하고, 선택한 가설에 대해 LangGraph 병렬 서브에이전트가 DB를 조회·분석한 뒤 액션 플랜을 제시합니다. 분석 완료 후에는 동일 세션에서 Q&A 대화를 이어갈 수 있습니다.

---

## 아키텍처

```
[Browser]
    │  /api/*
    ▼
[Frontend]  Vue 3 + Vite  :5174
    │  /api/* → proxy
    ▼
[Backend]  Spring Boot  :8080
    │  /internal/*
    ▼
[AI Server]  FastAPI + LangGraph  :8000
    │
    ├─ RAG (pgvector)
    ├─ Stateful Graph (AsyncPostgresSaver)
    └─ 병렬 서브에이전트 (Send API)
           ├─ ProcessHistoryAgent  (공정이력 조회)
           ├─ ReturnHistoryAgent   (반송이력 조회)
           ├─ TestResultAgent      (테스트결과 조회)
           └─ LongTermAgent        (장기이력 백그라운드)
                         │
                    [PostgreSQL + pgvector]  :5432
                    (앱 데이터 + LangGraph 체크포인트 공용)
```

### 분석 흐름

```
[1] 불량 입력
      │ POST /api/chat/agent  { action: "start" }
      ▼
[2] 가설 목록 반환  (RAG 검색 → LLM)
      │ 사용자가 가설 선택
      ▼
[3] 에이전트 선택  (토글 ON/OFF)
      │ POST /api/chat/agent  { action: "select_hypothesis" }
      ▼
[4] 병렬 에이전트 실행  (LangGraph Send API)
      ├─ 공정이력 / 반송이력 / 테스트결과 → 즉시 결과 반환
      └─ 장기이력 (선택 시) → 백그라운드 실행, task_id 반환
      │ 폴링: GET /api/chat/bg-status/{taskId}
      │ POST /api/chat/agent  { action: "resume_long_term" }
      ▼
[5] 최종 종합 액션 플랜  (선택된 에이전트 결과 통합)
      │ POST /api/chat/agent  { action: "chat" }
      ▼
[6] Q&A 대화  (동일 세션, 분석 결과 기반 추가 질문)
```

> **Stateful Graph**: LangGraph `interrupt()` / `Command(resume=...)` + `AsyncPostgresSaver`로
> 서버 재시작 후에도 `session_id`(= `thread_id`)로 세션 복원 가능.

---

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Frontend | Vue 3, Vite |
| Backend | Spring Boot, Java 17 |
| AI Server | FastAPI, LangGraph 1.x, LangChain, OpenAI GPT-4o-mini |
| Persistence | PostgreSQL 16 + pgvector (앱 DB + LangGraph 체크포인트 공용) |

---

## Docker로 전체 실행

### 1. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열고 OpenAI API 키를 입력합니다:

```env
OPENAI_API_KEY=sk-...
```

나머지 값은 기본값으로 Docker Compose와 연동됩니다.

### 2. 실행

```bash
docker compose up --build
```

| 서비스 | 호스트 접속 주소 |
|---|---|
| Frontend | http://localhost:5175 |
| Backend API | http://localhost:8081 |
| AI Server API | http://localhost:8001 |
| PostgreSQL | localhost:5433 |

### 3. 종료

```bash
docker compose down
```

DB 볼륨(앱 데이터 + LangGraph 체크포인트)까지 초기화:

```bash
docker compose down -v
```

---

## 로컬 개발 (터미널별 서버 실행)

### 사전 준비

- Python 3.11+
- Java 17+, Maven 3.8+
- Node.js 20+

### DB만 Docker로 실행

```bash
docker compose up postgres -d
```

PostgreSQL이 `localhost:5433`에서 실행됩니다.

### 터미널 1 — AI Server

```bash
cd display_defect_chatbot

# 최초 1회: 가상환경 생성 및 패키지 설치
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r ai_server/requirements.txt

# .env의 POSTGRES_HOST를 localhost로 변경 (로컬 개발 시)
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5433

uvicorn ai_server.server:app --reload --port 8000
```

> 시작 시 LangGraph 체크포인트 테이블(`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`)이 자동 생성됩니다.

### 터미널 2 — Backend

```bash
cd display_defect_chatbot/backend
mvn spring-boot:run
```

Windows PowerShell:
```powershell
$env:POSTGRES_HOST="localhost"; $env:POSTGRES_PORT="5433"
$env:INTERNAL_AI_SERVER_URL="http://localhost:8000"
mvn spring-boot:run
```

### 터미널 3 — Frontend

```bash
cd display_defect_chatbot/frontend
npm install
npm run dev
```

> `vite.config.js` proxy target이 `http://backend:8080`으로 설정되어 있습니다.
> 로컬 개발 시 `http://localhost:8080`으로 변경이 필요합니다.

---

## API 레퍼런스

### AI Server (내부용)

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/internal/agent` | 그래프 start / resume (action 기반) |
| `GET` | `/internal/bg-status/{task_id}` | 장기이력 백그라운드 작업 상태 |
| `POST` | `/internal/ingest` | RAG 문서 색인 |
| `DELETE` | `/internal/delete/{doc_id}` | RAG 문서 삭제 |
| `GET` | `/internal/health` | 헬스체크 |

#### `/internal/agent` action 종류

| action | 요청 필드 | 응답 필드 |
|---|---|---|
| `start` | company, defectDescription, productId, enabledAgents | hypotheses |
| `select_hypothesis` | selectedHypothesis, enabledAgents | agentResults, longTermTaskId |
| `resume_long_term` | longTermResult | finalActionPlan |
| `chat` | userMessage | reply |

### Backend (프론트용)

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/api/chat/agent` | AI Server `/internal/agent` 프록시 |
| `GET` | `/api/chat/bg-status/{taskId}` | 장기이력 상태 프록시 |

---

## DB 설정

### 자동 초기화

Docker Compose로 실행하면 `db/init.sql`이 자동으로 실행되어 테이블과 Mock 데이터가 생성됩니다.

### DB 구성

| 테이블 | 용도 |
|---|---|
| `products` | 제품 마스터 (LOT-A001 ~ LOT-D002) |
| `defect_cases` | 불량 케이스 (Dead Pixel, Hot Pixel 등) |
| `process_history` | 공정이력 (CVD, Photo, Etch 등) |
| `return_history` | 반송이력 (반송 사유, 수량, 심각도) |
| `test_results` | 테스트 결과 (측정값, 스펙 범위) |
| `background_tasks` | 장기이력 백그라운드 작업 추적 |
| `langchain_pg_collection` | pgvector RAG 문서 컬렉션 |
| `langchain_pg_embedding` | pgvector 임베딩 벡터 |
| `checkpoints` | LangGraph 세션 체크포인트 (자동 생성) |
| `checkpoint_blobs` | LangGraph 체크포인트 Blob (자동 생성) |
| `checkpoint_writes` | LangGraph 인터럽트 Write (자동 생성) |

### RAG 문서 색인

AI Server 실행 후 mock 데이터를 pgvector에 색인합니다:

```bash
for f in corrective_action_guide display_failure_cases equipment_sop \
          oled_amoled_failure_cases process_failure_history quality_standards; do
  curl -X POST "http://localhost:8000/internal/ingest?doc_id=$f" \
    -F "file=@ai_server/mock_data/${f}.txt"
done
```

---

## 환경변수 레퍼런스

| 변수 | 기본값 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | (필수) | OpenAI API 키 |
| `POSTGRES_HOST` | `postgres` | DB 호스트 (Docker: `postgres`, 로컬: `localhost`) |
| `POSTGRES_PORT` | `5432` | DB 포트 |
| `POSTGRES_USER` | `postgres` | DB 사용자 |
| `POSTGRES_PASSWORD` | `1234` | DB 비밀번호 |
| `POSTGRES_DB` | `defect_db` | DB 이름 |
| `MODEL_NAME` | `gpt-4o-mini` | 사용할 OpenAI 모델 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 임베딩 모델 |
| `LOG_GRAPH_ENABLED` | `false` | LangGraph 노드 상태 로깅 활성화 |
| `LOG_GRAPH_TARGET` | `console` | 로그 출력 대상 (`console` / `file` / `both`) |
| `LOG_GRAPH_FILE` | `logs/graph.log` | 로그 파일 경로 |
| `LOG_GRAPH_LEVEL` | `INFO` | 로그 레벨 |
| `INTERNAL_AI_SERVER_URL` | `http://localhost:8000` | Backend → AI Server URL |
