# Stateful Agent Refactoring Design

**Date:** 2026-03-09
**Scope:** AI Server, Backend (Spring), Frontend (Vue)

---

## Overview

현재 `/analyze` + `/investigate` 두 단계 API를 단일 `POST /internal/agent` 엔드포인트로 통합하고, LangGraph `interrupt()`/`Command(resume=...)` 패턴 + PostgresSaver를 이용한 stateful 그래프로 리팩토링한다.

---

## Graph Flow

```
START
  │
  ▼
hypothesis_node          ← RAG 검색 + 가설 생성
  │  interrupt()         → { hypotheses: [...] } 반환
  │  ← Command(resume=selected_hypothesis)
  ▼
investigation_dispatch   ← Send API 병렬 팬아웃
  ├── process_history_node
  ├── return_history_node
  ├── test_result_node
  └── long_term_node     ← 백그라운드 시작, task_id 저장
  │  interrupt()         → { agent_results (raw), long_term_task_id } 반환
  │  ← Command(resume=long_term_result)   [프론트 폴링 완료 후 호출]
  ▼
final_synthesis_node     ← 3개 에이전트 + 장기이력 모두 포함 최종 종합
  │  interrupt()         → { final_action_plan } 반환
  │  ← Command(resume=user_message)
  ▼
chat_node                ← Q&A 루프
  │  interrupt()         → { reply } 반환
  │  ← Command(resume=next_user_message)
  └──────────────────────(루프)
```

---

## State

```python
class DefectAnalysisState(TypedDict):
    # ── 입력 (불변) ──────────────────────────
    company: str
    defect_description: str
    product_id: str
    session_id: str
    enabled_agents: list[str]

    # ── 가설 단계 ────────────────────────────
    hypotheses: list[str]
    selected_hypothesis: str

    # ── 에이전트 결과 (reducer: 최신값 교체) ──
    process_history_result: Annotated[Optional[AgentAnalysisResult], lambda _, u: u]
    return_history_result:  Annotated[Optional[AgentAnalysisResult], lambda _, u: u]
    test_result:            Annotated[Optional[AgentAnalysisResult], lambda _, u: u]
    long_term_task_id:      Annotated[Optional[str], lambda _, u: u]
    long_term_result:       Annotated[Optional[str], lambda _, u: u]

    # ── 최종 출력 ────────────────────────────
    final_action_plan: str

    # ── Q&A 대화 이력 ─────────────────────────
    messages: Annotated[list, add_messages]
```

**Notes:**
- `process_step` 필드 없음 — 현재 단계는 PostgresSaver가 내부적으로 관리
- `messages`는 `add_messages` reducer로 Q&A 이력 누적
- 기존 `SubAgentInput` 분리 구조 유지 (Send API 팬아웃용)

---

## API

### AI Server

| Method | Path | 역할 |
|--------|------|------|
| `POST` | `/internal/agent` | 모든 단계 처리 (start / resume) |
| `GET`  | `/internal/bg-status/{task_id}` | 장기이력 폴링 (유지) |

**Request body:**
```json
{
  "session_id": "uuid",
  "action": "start | select_hypothesis | resume_long_term | chat",
  "company": "SDC",
  "defect_description": "...",
  "product_id": "LOT-A001",
  "enabled_agents": ["process_history", "return_history", "test_result", "long_term"],
  "selected_hypothesis": "가설1: ...",
  "long_term_result": "...",
  "user_message": "추가 질문"
}
```

**Response (action별):**

| action | 응답 필드 |
|--------|-----------|
| `start` | `{ hypotheses: [...] }` |
| `select_hypothesis` | `{ agent_results: {...}, long_term_task_id: "..." }` |
| `resume_long_term` | `{ final_action_plan: "..." }` |
| `chat` | `{ reply: "..." }` |

**AI Server 내부 로직:**
```python
@app.post("/internal/agent")
async def agent_endpoint(req: AgentRequest):
    config = {"configurable": {"thread_id": req.session_id}}

    if req.action == "start":
        result = await graph.ainvoke(initial_state, config=config)
    else:
        resume_value = {
            "select_hypothesis": req.selected_hypothesis,
            "resume_long_term":  req.long_term_result,
            "chat":              req.user_message,
        }[req.action]
        result = await graph.ainvoke(Command(resume=resume_value), config=config)

    return parse_interrupt_value(result)
```

### Backend (Spring)

**제거:**
- `POST /api/chat/analyze`
- `POST /api/chat/investigate`
- `POST /api/chat/agent/{agentName}`

**신규:**
- `POST /api/chat/agent`
- `GET  /api/chat/bg-status/{taskId}` (유지)

**신규 DTO:**
```java
// AgentRequest.java
String sessionId, action, company, defectDescription, productId;
List<String> enabledAgents;
String selectedHypothesis, longTermResult, userMessage;

// AgentResponse.java
String action;
List<String> hypotheses;
Map<String, Object> agentResults;
String longTermTaskId, finalActionPlan, reply;
```

---

## Infrastructure

### 패키지 추가 (AI Server)
```
langgraph-checkpoint-postgres
psycopg[binary,pool]
```

### PostgresSaver 설정
```python
# ai_server/infra/checkpointer.py
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def create_checkpointer(pg_url: str) -> AsyncPostgresSaver:
    checkpointer = AsyncPostgresSaver.from_conn_string(pg_url)
    await checkpointer.setup()  # LangGraph 체크포인트 테이블 자동 생성
    return checkpointer
```

- 기존 `pgvector/pgvector:pg16` PostgreSQL 인스턴스 공유
- `docker-compose.yml` 변경 없음

### config.py 추가
```python
pg_sync_url: str  # postgresql://... (psycopg3용, AsyncPostgresSaver에 전달)
# 기존 pg_async_url (asyncpg용) 유지
```

### lifespan 업데이트
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    embedding = OpenAIEmbeddings(model=settings.embedding_model)
    app.state.vsm = await VectorStoreManager.create(settings.pg_async_url, embedding)
    app.state.checkpointer = await create_checkpointer(settings.pg_sync_url)
    app.state.graph = build_graph(app.state.checkpointer)
    yield
```

---

## Frontend (Vue)

### useDefectChat.js 변경
- `analyze()` + `runAllEnabled()` → 단일 `callAgent(action, payload)` 함수
- `step` 관리: 서버 응답의 `action` 필드로 현재 단계 판별
- 장기이력 폴링 완료 → 자동으로 `callAgent("resume_long_term", { longTermResult })` 호출
- Q&A: `callAgent("chat", { userMessage })`

---

## Files to Change

| 파일 | 변경 유형 |
|------|-----------|
| `ai_server/agents/state.py` | 수정 (messages, long_term_result 추가) |
| `ai_server/agents/graph.py` | 전면 재작성 (interrupt 기반) |
| `ai_server/agents/main_agent.py` | 제거 → hypothesis_node로 흡수 |
| `ai_server/agents/synthesis_node.py` | 수정 (final_synthesis_node로 변경) |
| `ai_server/agents/sub/long_term.py` | 유지 |
| `ai_server/infra/checkpointer.py` | 신규 |
| `ai_server/config.py` | pg_sync_url 추가 |
| `ai_server/server.py` | 전면 재작성 (단일 /agent 엔드포인트) |
| `backend/.../ChatController.java` | 수정 |
| `backend/.../ChatService.java` | 수정 |
| `backend/.../dto/AgentRequest.java` | 신규 |
| `backend/.../dto/AgentResponse.java` | 신규 |
| `frontend/src/composables/useDefectChat.js` | 수정 |
| `frontend/src/api/defectApi.js` | 수정 |
| `.env.example` | pg_sync_url 추가 |
