# NCS RAG Chatbot — 아키텍처 마이그레이션 설계

**작성일:** 2026-02-19
**상태:** 승인됨

---

## 1. 배경 및 목표

현재 FastAPI 단일 서버로 운영 중인 NCS RAG Chatbot을 확장성 있는 멀티 서버 아키텍처로 전환한다.

**주요 변경 사항:**
- 일부 백엔드 로직을 Spring Boot MVC로 마이그레이션
- Vector DB 전용이던 구조를 PGVector(벡터) + Oracle(관계형)로 분리
- 프롬프트 하드코딩 → Redis DB화
- Arize Phoenix 기반 Agent 모니터링/평가 시스템 구축

---

## 2. 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (Vue.js)                   │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP
┌───────────────────────▼─────────────────────────────────┐
│               Spring Boot (8080) - API Gateway           │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ DocumentCtrl │  │ CategoryCtrl │  │  ChatController│  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         │ MyBatis          │ MyBatis            │ WebClient│
│  ┌──────▼───────────────────────────┐          │          │
│  │         Oracle DB                │          │          │
│  │  - documents (doc_id, meta...)   │          │          │
│  │  - ncs_categories                │          │          │
│  └──────────────────────────────────┘          │          │
└───────────────────────────────────────────────┬┘
                                                │ REST (내부)
┌───────────────────────────────────────────────▼─────────┐
│               Python FastAPI (8000) - AI Server          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  LangChain Agent                                     │ │
│  │    ├── Redis       → 시스템 프롬프트 로드             │ │
│  │    ├── PGVector    → doc_id 기반 벡터 검색           │ │
│  │    └── Arize Phoenix → OpenTelemetry 트레이싱        │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**서버 역할 분리:**

| 서버 | 기술 | 담당 역할 |
|------|------|-----------|
| Spring Boot | Java 17, MVC, MyBatis | PDF CRUD, 문서 레지스트리, API Gateway |
| Python FastAPI | LangChain, PGVector | RAG 시스템, AI 추론, 벡터 검색 |
| Oracle DB | JDBC | 문서 메타데이터, NCS 카테고리 |
| PGVector | PostgreSQL + pgvector | 벡터 임베딩 (doc_id 참조) |
| Redis | spring-data-redis | 시스템 프롬프트 템플릿 |
| Arize Phoenix | Docker self-hosted | Agent 트레이싱 및 모니터링 |

---

## 3. Document Registry 패턴

### 3.1 기존 구조의 문제점

```
[기존] PGVector 테이블
id | embedding | main_category | sub_category | source | page
                └──── 메타데이터 필터링을 PGVector 내부에서 직접 수행 ────┘
```

- 카테고리가 추가될 때마다 PGVector 스키마 변경 필요
- 관계형 데이터(카테고리 계층, 문서 상태)와 벡터 데이터가 혼재
- 문서 삭제/수정 시 일관성 보장 어려움

### 3.2 변경된 구조

```
[변경] Oracle documents 테이블
doc_id | filename | main_category | sub_category | page_count | status

[변경] PGVector 테이블
id | embedding | doc_id | page
                └── Oracle doc_id 참조
```

### 3.3 채팅 요청 흐름

```
1. Frontend → Spring POST /api/chat { query, main_category, sub_category }
2. Spring   → Oracle: SELECT doc_id WHERE main_category = ? AND sub_category = ?
3. Spring   → Python POST /internal/chat { query, doc_ids: ["uuid1", ...] }
4. Python   → PGVector: similarity_search WHERE doc_id IN (doc_ids)
5. Python   → Redis: 시스템 프롬프트 로드
6. Python   → LangChain Agent 실행 + Phoenix 트레이싱
7. Python   → Spring → Frontend 응답 반환
```

### 3.4 Oracle DB 스키마

```sql
-- 문서 레지스트리
CREATE TABLE documents (
    doc_id        VARCHAR2(36)  PRIMARY KEY,   -- UUID
    filename      VARCHAR2(255) NOT NULL,
    main_category VARCHAR2(100),
    sub_category  VARCHAR2(100),
    page_count    NUMBER,
    upload_date   DATE DEFAULT SYSDATE,
    status        VARCHAR2(20) DEFAULT 'PENDING'
    -- status: PENDING | INDEXED | FAILED
);

-- NCS 카테고리 마스터
CREATE TABLE ncs_categories (
    main_category VARCHAR2(100) NOT NULL,
    sub_category  VARCHAR2(100) NOT NULL,
    CONSTRAINT pk_ncs_cat PRIMARY KEY (main_category, sub_category)
);
```

---

## 4. Spring Boot MVC 구조

```
backend/src/main/java/com/ncs/backend/
├── controller/
│   ├── DocumentController.java     # PDF 업로드/CRUD
│   ├── CategoryController.java     # NCS 카테고리 조회
│   ├── ChatController.java         # AI 서버 프록시
│   └── PromptController.java       # Redis 프롬프트 관리
│
├── service/
│   ├── DocumentService.java        # 문서 비즈니스 로직
│   ├── CategoryService.java        # 카테고리 조회
│   ├── ChatService.java            # Python AI 서버 WebClient 호출
│   └── PromptService.java          # Redis 프롬프트 CRUD
│
├── mapper/
│   ├── DocumentMapper.java         # MyBatis Mapper
│   └── CategoryMapper.java
│
├── model/
│   ├── Document.java               # doc_id, filename, category, status
│   └── Category.java
│
├── dto/
│   ├── ChatRequest.java            # query, main_category, sub_category
│   ├── ChatResponse.java           # answer, sources
│   ├── InternalChatRequest.java    # query, doc_ids (Python 전달용)
│   └── DocumentUploadResponse.java
│
└── config/
    ├── WebClientConfig.java        # Python AI 서버 WebClient 설정
    └── RedisConfig.java            # Redis 연결 설정
```

**Spring REST API 목록:**

| Method | URL | 역할 |
|--------|-----|------|
| POST | `/api/documents` | PDF 업로드 (Oracle 저장 + Python ingest 호출) |
| GET | `/api/documents` | 문서 목록 조회 |
| DELETE | `/api/documents/{id}` | 문서 삭제 |
| GET | `/api/categories` | NCS 카테고리 조회 |
| POST | `/api/chat` | AI 채팅 (Python 프록시) |
| GET | `/api/prompts/{key}` | 프롬프트 조회 |
| PUT | `/api/prompts/{key}` | 프롬프트 수정 |

---

## 5. Python AI 서버 구조

```
src/
├── main.py             # FastAPI 앱 진입점 (/internal/* 엔드포인트)
├── agent.py            # ChatAgent (프롬프트를 Redis에서 로드)
├── vector_store.py     # PGVectorStore (doc_id IN 필터 방식으로 변경)
├── tool.py             # retrieve_context tool (doc_ids 파라미터 추가)
├── embeddings.py       # 임베딩 모델 (유지)
├── ingest.py           # PDF → 벡터 저장 (doc_id 함께 저장)
├── prompt_loader.py    # Redis에서 프롬프트 로드 (신규)
└── tracing.py          # Arize Phoenix OpenTelemetry 설정 (신규)
```

**Python 내부 API (Spring에서만 호출):**

| Method | URL | 역할 |
|--------|-----|------|
| POST | `/internal/ingest` | doc_id + PDF 경로 → 벡터 저장 |
| POST | `/internal/chat` | query + doc_ids → AI 응답 |

---

## 6. Redis 프롬프트 관리

**저장 구조:**
```
Key: prompt:rag_system_prompt
Value: "너는 NCS(국가직무능력표준) 문서 전문가야. 다음 참고 문서를 바탕으로 정확하고 친절하게 답변해줘.\n\n{context}"

Key: prompt:agent_system_prompt
Value: "너는 NCS 문서에서 정보를 검색하여 답변해주는 AI야. retrieve_context 도구를 적극 사용해줘."
```

- **Spring** (`PromptService`): 프롬프트 CRUD (관리자용)
- **Python** (`prompt_loader.py`): 서버 시작 시 또는 요청 시 Redis에서 로드

---

## 7. Arize Phoenix 모니터링

**운영 방식:** Docker self-hosted (로컬)

```bash
# Phoenix 실행
docker run -p 6006:6006 arizephoenix/phoenix:latest
```

**계측 대상:**
- LangChain Agent 실행 전체 흐름
- LLM 호출 latency / 입출력 토큰 수
- `retrieve_context` 도구 호출 및 반환 문서
- 벡터 검색 결과 품질

**Python tracing.py 설정:**
```python
# OpenTelemetry + Phoenix exporter 설정
# LangChain 자동 계측 (LangChainInstrumentor)
# Phoenix 대시보드: http://localhost:6006
```

---

## 8. 단계별 구현 계획

### Phase 1 — Spring 기반 구조 + Oracle 연동
- Spring MVC 패키지 구조 생성
- Oracle DataSource 설정 (`application.properties`)
- `documents`, `ncs_categories` 테이블 DDL 작성
- `DocumentController/Service/Mapper` CRUD 구현
- `CategoryController/Service/Mapper` 구현

### Phase 2 — Document Registry 패턴 + PGVector 개편
- `ingest.py` 수정: `doc_id`를 PGVector에 함께 저장
- `vector_store.py` 수정: `doc_id IN` 필터 기반 검색
- `tool.py` 수정: `doc_ids` 파라미터 기반 검색으로 변경
- Python `/internal/ingest`, `/internal/chat` API 구현
- Spring `DocumentService`에서 PDF 업로드 시 Python ingest 호출 연동

### Phase 3 — Redis 프롬프트 DB화
- Spring `spring-data-redis` 의존성 추가
- `PromptController/Service` 구현 (Redis CRUD)
- Python `prompt_loader.py` 구현
- `agent.py` 수정: 하드코딩 프롬프트 → Redis 로드로 교체

### Phase 4 — Spring API Gateway + ChatController
- `WebClientConfig` 설정 (Python base URL)
- `ChatController → ChatService → WebClient → Python` 구현
- 프론트엔드 API 호출 대상을 Spring(8080)으로 전환
- 기존 `server.py`의 `/api/chat`, `/api/categories` 제거

### Phase 5 — Arize Phoenix 모니터링 구축
- Docker로 Phoenix 로컬 실행
- `tracing.py` 구현 (OpenTelemetry + Phoenix exporter)
- LangChain 자동 계측 (`LangChainInstrumentor`) 설정
- Agent 트레이스 및 대시보드 검증

**Phase 의존 관계:**
```
Phase 1 → Phase 2 → Phase 4   (메인 흐름, 순차 진행)
Phase 3 ─────────────────────  (Phase 1 완료 후 독립 진행 가능)
Phase 5 ──────────────────────  (Phase 2 완료 후 진행)
```

---

## 9. 기술 스택 요약

| 항목 | 기술 |
|------|------|
| Spring Boot | 4.0.2, Java 17 |
| Spring 의존성 | WebMVC, MyBatis, spring-data-redis, WebClient |
| Python | FastAPI, LangChain, langchain-postgres |
| Oracle JDBC | ojdbc11 |
| Vector DB | PostgreSQL + pgvector (langchain-postgres) |
| Cache/Prompt | Redis |
| Embedding | OpenAI text-embedding-3-small |
| LLM | gpt-4o-mini |
| Monitoring | Arize Phoenix (Docker self-hosted) |
| Frontend | Vue.js + Vite |
