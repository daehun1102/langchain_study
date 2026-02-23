# NCS RAG Chatbot

NCS(국가직무능력표준) 문서를 기반으로 질문에 답변하는 RAG(Retrieval-Augmented Generation) 챗봇입니다.

Spring Boot API Gateway + Python AI Server 멀티 서버 아키텍처로 구성되며, Oracle DB(메타데이터)와 PGVector(벡터 임베딩)를 분리하는 Document Registry 패턴을 사용합니다.

---

## 아키텍처

```
Frontend (Vue.js :5174)
        │ HTTP
        ▼
Spring Boot (:8080) — API Gateway
  ├── DocumentController  → Oracle DB (문서 메타데이터)
  ├── CategoryController  → Oracle DB (NCS 카테고리)
  ├── ChatController      → Python AI 서버로 프록시
  └── PromptController    → Redis (시스템 프롬프트)
        │ REST (내부)
        ▼
Python FastAPI (:8000) — AI 서버 (외부 미노출)
  ├── /internal/ingest  → PGVector (PDF 벡터 저장)
  └── /internal/chat    → LangChain Agent + PGVector 검색
        │
        ├── Oracle DB   → doc_id 기반 문서 메타데이터
        ├── PGVector    → doc_id 참조 벡터 임베딩
        ├── Redis       → 시스템 프롬프트 로드
        └── Phoenix     → OpenTelemetry 트레이싱
```

### 서버별 역할

| 서버 | 포트 | 기술 | 역할 |
|------|------|------|------|
| Spring Boot | 8080 | Java 17, MVC, MyBatis | API Gateway, PDF CRUD, Oracle 연동 |
| Python FastAPI | 8000 | FastAPI, LangChain, LangGraph | RAG Agent, 벡터 검색 (내부 전용) |
| Oracle DB | 1521 | Oracle 21c | 문서 메타데이터, NCS 카테고리 |
| PostgreSQL | 5432 | pgvector | 벡터 임베딩 (doc_id 참조) |
| Redis | 6379 | Redis | 시스템 프롬프트 템플릿 |
| Arize Phoenix | 6006/4317 | Docker | Agent 트레이싱 대시보드 |
| Vue.js | 5174 | Vite | 프론트엔드 |

---

## 설치 및 설정

### 필수 조건

- **Python 3.10+**
- **Java 17+**
- **Node.js 18+**
- **Docker** (Redis, Arize Phoenix 실행용)
- **Oracle 21c** (로컬 또는 Docker)
- **PostgreSQL** (pgvector 확장 포함)
- **OpenAI API Key**

### 1. Python 환경 설정

```bash
# 가상환경 생성 및 활성화
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# 패키지 설치
pip install -r ai_server/requirements.txt
```

### 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다.

```ini
OPENAI_API_KEY=sk-your-api-key-here
DB_CONNECTION=postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db
REDIS_HOST=localhost
REDIS_PORT=6379
PHOENIX_HOST=localhost
PHOENIX_GRPC_PORT=4317
```

### 3. Oracle DB 초기화

DBeaver에서 `backend/src/main/resources/sql/schema.sql`을 실행합니다.

```
실행 방법:
1. DBeaver SQL 편집기에서 schema.sql 열기
2. Oracle 21c 연결 선택
3. Ctrl+A (전체 선택) → Alt+X (스크립트 실행)
※ "Ignore errors during script execution" 체크 권장
```

생성 테이블:
- `documents` — doc_id(UUID), filename, main_category, sub_category, status
- `ncs_categories` — 9개 NCS 카테고리 초기 데이터 포함

### 4. Spring Boot 설정

`backend/src/main/resources/application.properties`에서 Oracle 접속 정보를 확인합니다.

```properties
spring.datasource.url=jdbc:oracle:thin:@//localhost:1521/xepdb1
spring.datasource.username=rag_user
spring.datasource.password=rag1234
```

### 5. PGVector 테이블 초기화 (최초 1회)

```bash
python ai_server/ingest.py init
```

---

## 실행 방법

### 서비스 기동 순서

```bash
# 1. Redis
docker run -d -p 6379:6379 --name redis redis:latest

# 2. Arize Phoenix (모니터링)
docker run -d --name arize-phoenix -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest

# 3. Python AI 서버
cd ai_server
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
uvicorn server:app --reload --port 8000

# 4. Spring Boot (새 터미널)
cd backend
./mvnw spring-boot:run

# 5. 프론트엔드 (새 터미널)
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5174` 접속

---

## 주요 기능

### PDF 문서 업로드

`POST /api/documents` (Spring)

1. Spring이 Oracle `documents` 테이블에 `PENDING` 상태로 메타데이터 저장
2. Python `/internal/ingest` 호출 → PDF를 청크로 분할 후 PGVector에 `doc_id`와 함께 저장
3. 완료 시 상태를 `INDEXED`로 업데이트

### RAG 채팅

`POST /api/chat` (Spring)

```json
{
  "query": "SW 아키텍처 수행관리의 핵심은?",
  "mainCategory": "정보기술개발",
  "subCategory": "SW아키텍쳐"
}
```

1. Spring → Oracle에서 카테고리에 맞는 `doc_id` 목록 조회
2. Spring → Python `/internal/chat` 호출 `{ query, doc_ids }`
3. Python → PGVector에서 `doc_id IN (...)` 필터 유사도 검색
4. Python → Redis에서 시스템 프롬프트 로드
5. LangGraph ReAct Agent 실행 → 응답 반환

### 프롬프트 관리

```bash
# 프롬프트 조회
GET http://localhost:8080/api/prompts

# 프롬프트 수정 (재배포 없이 즉시 반영)
PUT http://localhost:8080/api/prompts/agent_system_prompt
{ "value": "새 프롬프트 내용..." }
```

### Agent 모니터링

Arize Phoenix 대시보드: `http://localhost:6006`

- LangChain Agent 실행 전체 흐름 트레이싱
- LLM 호출 latency / 입출력 토큰 수
- `retrieve_context` 도구 호출 및 반환 문서 확인

---

## Spring REST API

| Method | URL | 설명 |
|--------|-----|------|
| `POST` | `/api/documents` | PDF 업로드 |
| `GET` | `/api/documents` | 문서 목록 조회 |
| `DELETE` | `/api/documents/{docId}` | 문서 삭제 |
| `GET` | `/api/categories` | NCS 카테고리 조회 |
| `POST` | `/api/chat` | AI 채팅 |
| `GET` | `/api/prompts` | 프롬프트 전체 조회 |
| `GET` | `/api/prompts/{key}` | 프롬프트 조회 |
| `PUT` | `/api/prompts/{key}` | 프롬프트 수정 |
| `DELETE` | `/api/prompts/{key}` | 프롬프트 삭제 |
| `GET` | `/api/health` | 헬스 체크 |

## Python 내부 API (Spring 전용)

| Method | URL | 설명 |
|--------|-----|------|
| `GET` | `/internal/health` | 헬스 체크 |
| `POST` | `/internal/ingest` | PDF 벡터 저장 |
| `POST` | `/internal/chat` | RAG 채팅 응답 생성 |

---

## 프로젝트 구조

```
ncs_rag_chatbot/
├── backend/                        # Spring Boot (Java)
│   └── src/main/
│       ├── java/com/ncs/backend/
│       │   ├── controller/         # REST 컨트롤러
│       │   ├── service/            # 비즈니스 로직
│       │   ├── mapper/             # MyBatis Mapper
│       │   ├── model/              # DB 엔티티
│       │   ├── dto/                # 요청/응답 DTO
│       │   └── config/             # CORS, RestClient, Redis 설정
│       └── resources/
│           ├── application.properties
│           ├── mapper/             # MyBatis XML
│           └── sql/schema.sql      # Oracle DDL
│
├── ai_server/                      # Python AI 서버
│   ├── server.py                   # FastAPI 앱 진입점
│   ├── requirements.txt            # Python 의존성
│   ├── agent.py                    # LangGraph ReAct Agent
│   ├── tool.py                     # retrieve_context 도구
│   ├── vector_store.py             # PGVectorStore (doc_id 필터)
│   ├── ingest.py                   # PDF → PGVector 적재
│   ├── prompt_loader.py            # Redis 프롬프트 로드
│   ├── tracing.py                  # Arize Phoenix OTel 설정
│   ├── embeddings.py               # OpenAI 임베딩 모델
│   ├── loader.py                   # PDF 로더
│   └── splitter.py                 # 문서 청크 분할
│
├── frontend/                       # Vue.js (Vite)
│   └── src/
│       ├── api/ncsApi.js           # Spring API 호출
│       └── composables/useChat.js
│
└── .env                            # 환경 변수 (gitignore)
```

---

## 기술 스택

| 항목 | 기술 |
|------|------|
| API Gateway | Spring Boot 4.0.2, Java 17, MVC, MyBatis |
| AI Server | Python FastAPI, LangChain, LangGraph |
| LLM | gpt-4o-mini |
| Embedding | text-embedding-3-small |
| Vector DB | PostgreSQL + pgvector (langchain-postgres) |
| Relational DB | Oracle 21c (ojdbc11) |
| Cache/Prompt | Redis (spring-data-redis) |
| Monitoring | Arize Phoenix (Docker, OpenTelemetry) |
| Frontend | Vue.js 3, Vite |
