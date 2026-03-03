# Display Defect Chatbot — 설계 문서

**작성일**: 2026-03-03
**프로젝트**: `display_defect_chatbot`
**참조**: `ncs_rag_chatbot` (동일 스택, 다른 도메인·에이전트)

---

## 1. 프로젝트 개요

삼성 디스플레이 제조 환경에서 발생하는 **제품 불량 및 반송 건**에 대해, 과거 데이터를 기반으로 고장 원인을 분석하고 담당자에게 **조치 방안을 제시하는 대화형 AI 챗봇**.

### 주요 시나리오

1. 엔지니어가 회사명 + 불량 증상을 챗봇에 입력
2. MainAnalysisAgent가 PGVector RAG를 통해 유사 과거 사례 검색 → 가설 2-3개 생성
3. 엔지니어가 가설 중 하나를 선택
4. LangGraph Send API로 4개 서브에이전트 병렬 실행:
   - **공정이력 에이전트**: PostgreSQL `process_history` 테이블 조회
   - **반송이력 에이전트**: PostgreSQL `return_history` 테이블 조회
   - **테스트결과 에이전트**: PostgreSQL `test_results` 테이블 조회
   - **장기이력 에이전트**: asyncio 백그라운드 Task로 실행 → 완료 시 파일 생성
5. SynthesisNode가 3개 결과를 종합 → 최종 조치안 출력
6. 장기이력 분석 완료 시 프론트엔드에 알림 + 파일 다운로드 제공

---

## 2. 시스템 아키텍처

```
┌──────────────────────────────────────────────────────┐
│              Frontend  Vue.js (:5174)                │
│   채팅 UI  |  가설 선택 버튼  |  서브에이전트 결과 패널  │
└────────────────────┬─────────────────────────────────┘
                     │ HTTP REST / SSE
┌────────────────────▼─────────────────────────────────┐
│            Spring Boot  API Gateway (:8080)          │
│  ChatController → /api/chat (FastAPI 프록시)         │
│  DocumentController → /api/documents (txt 업로드)    │
│  SessionController → /api/sessions/{id}/files (bg)  │
│  ProductController → /api/products (제품/케이스 CRUD) │
└────────────────────┬─────────────────────────────────┘
                     │ Internal REST
┌────────────────────▼─────────────────────────────────┐
│              FastAPI  AI Server (:8000)              │
│                                                      │
│  [MainAnalysisAgent]  RAG 가설 생성                  │
│       ↓ 가설 선택 (LangGraph interrupt)              │
│  [dispatch_node → Send API 병렬 팬아웃]              │
│   ├── ProcessHistoryAgent  → SQL 공정이력            │
│   ├── ReturnHistoryAgent   → SQL 반송이력            │
│   ├── TestResultAgent      → SQL 테스트결과          │
│   └── LongTermAgent        → asyncio 백그라운드      │
│  [SynthesisNode]  최종 조치안 생성                   │
└────┬──────────────────────────────────────────────┘
     │
┌────▼──────────────┐
│   PostgreSQL      │
│  ├── Relational   │  process_history, return_history
│  │   tables       │  test_results, defect_cases, products
│  └── PGVector     │  defect_vectors (txt 문서 청크)
└───────────────────┘
```

---

## 3. LangGraph 그래프 설계

### State 정의

```python
class DefectAnalysisState(TypedDict):
    thread_id: str
    company: str
    defect_description: str
    hypotheses: list[str]
    selected_hypothesis: str

    # Annotated reducer로 병렬 결과 합산
    process_history_result: Annotated[list, operator.add]
    return_history_result: Annotated[list, operator.add]
    test_result: Annotated[list, operator.add]

    # 백그라운드 작업
    long_term_task_id: str
    long_term_file_path: str

    # 최종 출력
    final_action_plan: str
```

### 그래프 노드 흐름

```
start
  └→ [main_analysis_node]   PGVector RAG → 가설 2-3개 생성
         ↓
  interrupt (사용자 가설 선택 대기)
         ↓
  [dispatch_node]            Send API 병렬 팬아웃
         ├──Send──→ [process_history_node]   process_history 조회
         ├──Send──→ [return_history_node]    return_history 조회
         ├──Send──→ [test_result_node]       test_results 조회
         └──Send──→ [long_term_node]         asyncio.create_task() 시작 → 즉시 반환
         ↓ (3개 완료 후 join)
  [synthesis_node]           3개 결과 + 가설 → 최종 조치안 생성
         ↓
  end
```

### 핵심 구현 포인트

- `dispatch_node`에서 `[Send("process_history_node", ...), ...]` 리스트 반환
- `long_term_node`는 `asyncio.create_task()`만 등록하고 즉시 반환 (논블로킹)
- 백그라운드 작업 완료 시 `background_files` 테이블에 기록 → Spring SSE로 프론트 알림
- `InMemorySaver` checkpointer로 다중 대화 세션 관리

---

## 4. DB 스키마 (PostgreSQL)

```sql
-- 제품 마스터
CREATE TABLE products (
    product_id      VARCHAR(50) PRIMARY KEY,
    model           VARCHAR(100),
    panel_size      VARCHAR(20),
    manufactured_at TIMESTAMP
);

-- 불량 케이스
CREATE TABLE defect_cases (
    case_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id   VARCHAR(50) REFERENCES products(product_id),
    company      VARCHAR(100),
    defect_type  VARCHAR(100),
    description  TEXT,
    reported_at  TIMESTAMP DEFAULT NOW()
);

-- 공정이력 (ProcessHistoryAgent 조회)
CREATE TABLE process_history (
    id           BIGSERIAL PRIMARY KEY,
    product_id   VARCHAR(50),
    process_step VARCHAR(100),
    equipment_id VARCHAR(50),
    operator_id  VARCHAR(50),
    result       VARCHAR(20),     -- PASS/FAIL/WARN
    measured_at  TIMESTAMP
);

-- 반송이력 (ReturnHistoryAgent 조회)
CREATE TABLE return_history (
    id            BIGSERIAL PRIMARY KEY,
    product_id    VARCHAR(50),
    return_reason VARCHAR(200),
    return_date   DATE,
    quantity      INT,
    severity      VARCHAR(20)     -- HIGH/MEDIUM/LOW
);

-- 테스트결과 (TestResultAgent 조회)
CREATE TABLE test_results (
    id              BIGSERIAL PRIMARY KEY,
    product_id      VARCHAR(50),
    test_type       VARCHAR(100),
    result          VARCHAR(20),
    measured_value  DECIMAL,
    spec_min        DECIMAL,
    spec_max        DECIMAL,
    tested_at       TIMESTAMP
);

-- 백그라운드 작업 추적
CREATE TABLE background_files (
    id           BIGSERIAL PRIMARY KEY,
    session_id   VARCHAR(100),
    file_path    VARCHAR(500),
    status       VARCHAR(20) DEFAULT 'PENDING',
    created_at   TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

---

## 5. 디렉토리 구조

```
display_defect_chatbot/
├── ai_server/
│   ├── server.py
│   ├── config.py
│   ├── requirements.txt
│   ├── agents/
│   │   ├── graph.py                  # LangGraph 메인 그래프
│   │   ├── main_agent.py             # RAG 가설 생성 노드
│   │   ├── synthesis_node.py         # 최종 조치안 종합 노드
│   │   └── sub/
│   │       ├── process_history.py
│   │       ├── return_history.py
│   │       ├── test_result.py
│   │       └── long_term.py
│   ├── tools/
│   │   ├── rag_tool.py
│   │   └── sql_tools.py
│   ├── infra/
│   │   ├── vector_store.py
│   │   ├── database.py               # AsyncEngine (SQLAlchemy)
│   │   ├── ingest.py
│   │   └── tracing.py
│   └── mock_data/
│       ├── pixel_failure_cases.txt
│       └── process_sop.txt
│
├── backend/
│   └── src/main/java/com/sdi/chatbot/
│       ├── controller/
│       │   ├── ChatController.java
│       │   ├── DocumentController.java
│       │   ├── ProductController.java
│       │   └── SessionController.java
│       ├── service/
│       ├── mapper/
│       └── model/
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ChatView.vue
│       │   ├── HypothesisSelector.vue
│       │   ├── AgentResultPanel.vue
│       │   └── BgTaskNotifier.vue
│       └── composables/
│           └── useDefectChat.js
│
├── db/
│   └── init.sql
│
├── docs/plans/
├── docker-compose.yml
└── .env
```

---

## 6. Tech Stack

| Layer | 기술 |
|-------|------|
| Frontend | Vue 3, Vite |
| Backend (API Gateway) | Spring Boot 4.x, Java 17, MyBatis |
| AI Server | FastAPI, LangGraph (Send API), LangChain |
| LLM | OpenAI gpt-4o-mini |
| Vector DB | PostgreSQL + pgvector |
| Relational DB | PostgreSQL (공정/반송/테스트 이력) |
| Tracing | Arize Phoenix (선택적) |
| Containerization | Docker Compose |

---

## 7. 주요 API 엔드포인트

### Spring Boot (:8080)
| Method | Path | 설명 |
|--------|------|------|
| POST | /api/chat | 채팅 메시지 전송 (FastAPI 프록시) |
| POST | /api/documents | txt 문서 업로드 |
| GET | /api/documents | 문서 목록 조회 |
| DELETE | /api/documents/{docId} | 문서 삭제 |
| GET | /api/products | 제품 목록 |
| GET | /api/sessions/{id}/files | 백그라운드 파일 상태 폴링 |

### FastAPI (:8000, internal)
| Method | Path | 설명 |
|--------|------|------|
| POST | /internal/chat | 에이전트 실행 |
| POST | /internal/ingest | txt 문서 벡터 색인 |
| DELETE | /internal/delete/{docId} | 벡터 삭제 |
| GET | /internal/bg-status/{taskId} | 백그라운드 작업 상태 |
