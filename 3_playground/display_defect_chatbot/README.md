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
[ai_server]  FastAPI + LangGraph  :8000
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

## AI 서버 그래프 상세 작동 원리

### 핵심: interrupt() + Command(resume=) + AsyncPostgresSaver

그래프는 단순한 Python 함수 호출이 아니라 **체크포인트 기반 상태 머신**입니다.

```
HTTP 요청 → graph.ainvoke() → interrupt() 에서 실행 중단 → HTTP 응답 반환
                                        │
                              AsyncPostgresSaver가
                              현재 상태 전체를 PostgreSQL에 직렬화
                                        │
다음 HTTP 요청 → Command(resume=값) → interrupt() 이후 지점부터 재개
```

각 HTTP 요청은 그래프를 처음부터 실행하는 것이 아니라 **마지막 interrupt 지점부터 이어서 실행**합니다.
`thread_id`(= `session_id`) 하나로 전체 대화 흐름이 식별되며, 서버 재시작 후에도 세션이 복원됩니다.

---

### 노드별 실행 흐름

#### [1] action: `start` → `hypothesis_node`

```
graph.ainvoke(initial_state, config={thread_id: session_id})

hypothesis_node
  ├─ VectorStore.similarity_search(defect_description, k=4)  ← RAG 검색
  ├─ LLM.ainvoke([SystemMessage, HumanMessage(증상 + RAG 문서)])  ← 가설 생성
  └─ interrupt({"hypotheses": ["가설1: ...", "가설2: ...", ...]})
                └─ HTTP 응답으로 반환
                   PostgreSQL에 상태 저장 (checkpoints 테이블)
```

#### [2] action: `select_hypothesis` → 병렬 팬아웃

```
graph.ainvoke(
  Command(resume={"selected_hypothesis": "가설1: ...", "enabled_agents": [...]}),
  config={thread_id: session_id}
)

hypothesis_node (interrupt 반환값 수신)
  ├─ selected_hypothesis, enabled_agents 상태 업데이트
  └─ route_to_agents (conditional edge)
       ├─ Send("process_history_node", sub_state)  ─┐
       ├─ Send("return_history_node",  sub_state)   ├─ LangGraph Send API
       ├─ Send("test_history_node",     sub_state)   │  (병렬 팬아웃)
       └─ Send("long_term_node",       sub_state)  ─┘ (enabled 시에만)

       ↓ 모든 선행 노드 완료 후 자동 fan-in ↓

await_long_term_node
  ├─ 4개 서브에이전트 결과 수집
  ├─ [장기이력 있을 때] interrupt({"agent_results": {...}, "long_term_task_id": "uuid"})
  └─ [장기이력 없을 때] interrupt({"agent_results": {...}, "long_term_task_id": null})
                └─ HTTP 응답으로 반환
                   PostgreSQL에 상태 저장
```

**Send API 팬아웃/팬인 상세:**

`route_to_agents`가 반환하는 `Send` 목록만큼 노드가 독립적으로 병렬 실행됩니다.
LangGraph는 `await_long_term_node`로 향하는 **모든 선행 노드가 완료**될 때까지 대기한 뒤 자동으로 fan-in합니다.

```
hypothesis_node
     │
     ├─ process_history_node ──┐
     ├─ return_history_node    ├─ (전부 완료) → await_long_term_node
     ├─ test_history_node       │
     └─ long_term_node        ─┘
```

각 서브에이전트 결과는 `Annotated[Optional[AgentAnalysisResult], lambda _, u: u]` reducer로 `DefectAnalysisState`에 병합됩니다.

#### [3] action: `resume_long_term` → `final_synthesis_node`

```
graph.ainvoke(Command(resume=long_term_result), config={thread_id: session_id})

await_long_term_node (interrupt 반환값 수신)
  ├─ long_term_result 상태 업데이트
  └─→ final_synthesis_node
        ├─ process_history_result + return_history_result + test_history_result + long_term_result
        ├─ LLM으로 최종 액션 플랜 생성
        └─→ chat_node
              └─ interrupt({"final_action_plan": "..."})
                       └─ HTTP 응답으로 반환
                          PostgreSQL에 상태 저장
```

> 장기이력이 비활성화된 경우, 프론트엔드는 `longTermTaskId: null`을 받으면 즉시 `resume_long_term` 요청을 빈 값으로 전송해 그래프를 자동으로 unblock합니다.

#### [4] action: `chat` → Q&A 루프

```
graph.ainvoke(Command(resume=user_message), config={thread_id: session_id})

chat_node (interrupt 반환값 = user_message 수신)
  ├─ SystemMessage(최종 액션 플랜 + 불량 정보 + 가설)
  ├─ messages 이력 (HumanMessage/AIMessage 누적)
  ├─ HumanMessage(user_message)
  ├─ LLM.ainvoke(messages)
  ├─ messages에 [HumanMessage, AIMessage] 추가  ← add_messages reducer
  └─→ chat_node (자기 자신으로 루프)
        └─ interrupt({"final_action_plan": "..."})
                 └─ HTTP 응답으로 반환 (reply = 마지막 AIMessage)
```

`chat_node → chat_node` 자기 루프 엣지 덕분에 Q&A는 별도 설계 없이 무한 반복됩니다.

---

### AsyncPostgresSaver 체크포인트 테이블

| 테이블 | 저장 내용 |
|---|---|
| `checkpoints` | 체크포인트 메타데이터 (thread_id, step, timestamp) |
| `checkpoint_blobs` | `DefectAnalysisState` 전체 직렬화 데이터 |
| `checkpoint_writes` | interrupt 직전까지 쌓인 write 목록 |

서버 기동 시 `checkpointer.setup()`으로 테이블이 자동 생성됩니다.
`thread_id = session_id`이므로 브라우저 탭마다 완전히 독립된 그래프 상태를 가집니다.

---

### config 주입 패턴

```python
# server.py — 모든 요청에서 vsm(VectorStoreManager)을 config로 전달
config = {
    "configurable": {
        "thread_id": req.session_id,
        "vsm": app.state.vsm,
    }
}

# hypothesis_node — RunnableConfig로 vsm 수신
async def hypothesis_node(state: DefectAnalysisState, config: RunnableConfig):
    vsm: VectorStoreManager = config["configurable"]["vsm"]
```

LangGraph는 `RunnableConfig` 파라미터가 있는 노드에 `config`를 **자동 주입**합니다.
`apply_middleware` 래퍼는 `**kwargs`를 사용해 이 주입을 방해하지 않고 그대로 전달합니다:

```python
async def wrapped(state: dict, **kwargs) -> dict:
    result = await node_fn(state, **kwargs)  # config 포함 전달
```

---

### 전체 상태(State) 생명주기

```
DefectAnalysisState
├─ company, defect_description, product_id, session_id   ← start 시 초기화, 불변
├─ enabled_agents                                         ← select_hypothesis 시 업데이트
├─ hypotheses, selected_hypothesis                        ← hypothesis_node 완료 시
├─ process_history_result                                 ← process_history_node 완료 시
├─ return_history_result                                  ← return_history_node 완료 시
├─ test_history_result                                    ← test_history_node 완료 시
├─ long_term_task_id                                      ← long_term_node 완료 시
├─ long_term_result                                       ← resume_long_term 수신 시
├─ final_action_plan                                      ← final_synthesis_node 완료 시
└─ messages: [HumanMessage, AIMessage, ...]               ← chat_node마다 누적 (add_messages)
```

이 전체 상태가 매 `interrupt()` 시점마다 PostgreSQL에 스냅샷됩니다.
`Command(resume=...)` 실행 시 스냅샷을 복원하고 새 값만 reducer로 merge합니다.

---

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Frontend | Vue 3, Vite |
| ai_server | FastAPI, LangGraph 1.x, LangChain, OpenAI GPT-4o-mini |
| Persistence | PostgreSQL 16 + pgvector (앱 DB + LangGraph 체크포인트 공용) |

---

## 실행 방법

```bash
# 1. DB 생성 및 초기화
psql -U postgres -h localhost -c "CREATE DATABASE defect_db;"

# Windows CMD
set PGCLIENTENCODING=UTF8 && psql -U postgres -h localhost -d defect_db -f db/init.sql

# macOS / Linux
PGCLIENTENCODING=UTF8 psql -U postgres -h localhost -d defect_db -f db/init.sql

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

> 시작 시 LangGraph 체크포인트 테이블(`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`)이 자동 생성됩니다.

---

## API 레퍼런스

### ai_server

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/api/chat/agent` | 그래프 start / resume (action 기반) |
| `GET` | `/api/chat/bg-status/{task_id}` | 장기이력 백그라운드 작업 상태 |
| `GET` | `/api/documents` | RAG 문서 목록 조회 |
| `POST` | `/api/documents` | RAG 문서 업로드 및 색인 |
| `DELETE` | `/api/documents/{doc_id}` | RAG 문서 삭제 |
| `GET` | `/api/health` | 헬스체크 |

#### `/api/chat/agent` action 종류

| action | 요청 필드 | 응답 필드 |
|---|---|---|
| `start` | company, defectDescription, productId, enabledAgents | hypotheses |
| `select_hypothesis` | selectedHypothesis, enabledAgents | agentResults, longTermTaskId |
| `resume_long_term` | longTermResult | finalActionPlan |
| `chat` | userMessage | reply |

---

## DB 설정

### 초기화

`db/init.sql`을 실행하면 테이블과 Mock 데이터가 생성됩니다. 위 실행 방법의 1단계를 참고하세요.

### DB 구성

| 테이블 | 용도 |
|---|---|
| `products` | 제품 마스터 (LOT-A001 ~ LOT-D002) |
| `defect_cases` | 불량 케이스 (Dead Pixel, Hot Pixel 등) |
| `process_history` | 공정이력 (CVD, Photo, Etch 등) |
| `return_history` | 반송이력 (반송 사유, 수량, 심각도) |
| `test_history` | 테스트 이력 (측정값, 스펙 범위) |
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
  curl -X POST "http://localhost:8000/api/documents" \
    -F "file=@ai_server/mock_data/${f}.txt"
done
```

---

## 환경변수 레퍼런스

| 변수 | 기본값 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | (필수) | OpenAI API 키 |
| `POSTGRES_HOST` | `localhost` | DB 호스트 |
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
