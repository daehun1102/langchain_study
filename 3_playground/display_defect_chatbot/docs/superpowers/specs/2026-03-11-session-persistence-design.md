# 대화 세션 DB 저장 설계

**날짜:** 2026-03-11
**대상:** `ai_server/` + `frontend/src/`
**목표:** 현재 localStorage 기반 세션 저장을 PostgreSQL DB로 완전 교체. 세션 Create/Read/Delete + 제목 수정(PATCH) 지원.

---

## 1. 배경 및 결정 사항

- **현재 상태:** 세션 데이터(`chatMessages`, `agentResults`, 폴링 상태 등)가 `localStorage`에만 저장됨. 브라우저 초기화 시 소실, 다른 기기에서 접근 불가.
- **목표:** PostgreSQL `chat_sessions` 테이블에 저장, FastAPI CRUD 엔드포인트 제공, 프런트엔드는 API 호출로 교체.
- **방식:** 단일 `chat_sessions` 테이블 + upsert 패턴 (방법 C 채택)
  - 세션 저장이 여러 시점에 호출되는 구조(에이전트 완료 후, 폴링 완료 후)와 호환
  - localStorage 완전 제거 (오프라인 캐시 미사용)

---

## 2. DB 스키마

```sql
-- ai_server/infra/migrations/002_add_chat_sessions.sql
CREATE TABLE IF NOT EXISTS chat_sessions (
    id                  TEXT PRIMARY KEY,
    title               TEXT NOT NULL DEFAULT '',
    product_id          TEXT NOT NULL DEFAULT '',
    defect_description  TEXT NOT NULL DEFAULT '',
    hypothesis          TEXT NOT NULL DEFAULT '',
    agent_results       JSONB NOT NULL DEFAULT '{}',
    chat_messages       JSONB NOT NULL DEFAULT '[]',
    enabled_agents      JSONB NOT NULL DEFAULT '{}',
    long_term_task_id   TEXT,
    long_term_status    TEXT NOT NULL DEFAULT 'PENDING',
    long_term_result    TEXT,
    final_action_plan   TEXT NOT NULL DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**필드 설명:**
- `id`: LangGraph `thread_id`와 동일한 UUID. Primary Key.
- `title`: 사용자 수정 가능 이름. 최초 저장 시 프런트에서 `{productId} — {hypothesis 앞 30자}`로 자동 생성하여 전달. 이후 PATCH로만 변경.
- `agent_results`: `{ process_history, return_history, test_history, long_term }` 각각 `{ analysis, suspectRows }`.
- `chat_messages`: 에이전트 카드 + 사용자 채팅 메시지 배열.
- `enabled_agents`: `{ process_history: bool, return_history: bool, test_history: bool, long_term: bool }` 형태의 객체. 프런트엔드 `enabledAgents` reactive 객체와 동일한 형식으로 저장.
- `long_term_task_id` + `long_term_status`: 세션 복원 시 폴링 재개에 필요.
- `final_action_plan`: 현재 localStorage에 누락된 필드. DB 저장으로 복원 가능하게 됨.

**마이그레이션 전략:**
- **신규 설치:** `db/init.sql`에 DDL 추가. DB 초기화 시 자동 적용.
- **기존 DB 업그레이드:** `infra/migrations/002_add_chat_sessions.sql`을 수동으로 실행 (`psql -f 002_add_chat_sessions.sql`). `CREATE TABLE IF NOT EXISTS`이므로 중복 실행 안전.
- Alembic 미사용. 기존 프로젝트 패턴 유지.

---

## 3. API 엔드포인트

리팩토링 설계(`2026-03-11-ai-server-refactor-design.md`)의 레이어 구조를 따름.
세션 CRUD는 비즈니스 로직 없이 단순 저장/조회이므로 서비스 레이어 없이 라우터에서 repository 직접 호출.

### 엔드포인트 목록

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/sessions` | 세션 목록 (최신순, 요약 정보만) |
| `GET` | `/api/sessions/{id}` | 세션 단건 전체 조회 |
| `PUT` | `/api/sessions/{id}` | 세션 upsert (전체 데이터 저장/업데이트) |
| `DELETE` | `/api/sessions/{id}` | 세션 삭제 |
| `PATCH` | `/api/sessions/{id}/title` | 제목만 업데이트 |

### Pydantic 모델 (`api/schemas.py`에 추가)

**모든 모델**은 기존 패턴과 동일하게 `ConfigDict(alias_generator=to_camel, populate_by_name=True)` 적용. 프런트엔드와 camelCase로 통신.

```python
class SessionUpsertRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    title: str                        # 프런트에서 자동 생성 후 전달
    product_id: str
    defect_description: str
    hypothesis: str
    agent_results: dict
    chat_messages: list
    enabled_agents: dict              # { process_history: bool, ... }
    long_term_task_id: Optional[str] = None
    long_term_status: str
    long_term_result: Optional[str] = None
    final_action_plan: str

class SessionSummary(BaseModel):
    """목록 조회용 — chatMessages 제외하여 응답 크기 최소화"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    title: str
    product_id: str
    hypothesis: str
    agent_results: dict   # LeftPanel의 ranAgents() 아이콘 표시에 필요 (키 존재 여부만 사용)
    updated_at: str

class SessionDetail(BaseModel):
    """단건 조회용 — 전체 필드 포함"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    title: str
    product_id: str
    defect_description: str
    hypothesis: str
    agent_results: dict
    chat_messages: list
    enabled_agents: dict
    long_term_task_id: Optional[str]
    long_term_status: str
    long_term_result: Optional[str]
    final_action_plan: str
    updated_at: str

class SessionTitleUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    title: str
```

---

## 4. Repository 구현 (`repositories/session_repo.py`)

### upsert SQL

`updated_at`은 `DEFAULT NOW()`가 INSERT에만 적용되므로, upsert의 DO UPDATE 절에서 명시적으로 `updated_at = NOW()` 설정.

```python
async def upsert_session(id: str, data: dict) -> dict:
    async with get_db_session() as session:
        result = await session.execute(
            text("""
                INSERT INTO chat_sessions (
                    id, title, product_id, defect_description, hypothesis,
                    agent_results, chat_messages, enabled_agents,
                    long_term_task_id, long_term_status, long_term_result,
                    final_action_plan
                ) VALUES (
                    :id, :title, :product_id, :defect_description, :hypothesis,
                    :agent_results::jsonb, :chat_messages::jsonb, :enabled_agents::jsonb,
                    :long_term_task_id, :long_term_status, :long_term_result,
                    :final_action_plan
                )
                ON CONFLICT (id) DO UPDATE SET
                    title               = EXCLUDED.title,
                    product_id          = EXCLUDED.product_id,
                    defect_description  = EXCLUDED.defect_description,
                    hypothesis          = EXCLUDED.hypothesis,
                    agent_results       = EXCLUDED.agent_results,
                    chat_messages       = EXCLUDED.chat_messages,
                    enabled_agents      = EXCLUDED.enabled_agents,
                    long_term_task_id   = EXCLUDED.long_term_task_id,
                    long_term_status    = EXCLUDED.long_term_status,
                    long_term_result    = EXCLUDED.long_term_result,
                    final_action_plan   = EXCLUDED.final_action_plan,
                    updated_at          = NOW()
                RETURNING id, title, product_id, hypothesis, agent_results, updated_at
            """),
            {**data, "id": id},
        )
        return dict(result.mappings().first())
```

### 기타 함수

```python
async def list_sessions() -> list[dict]         # SELECT 요약 필드, ORDER BY updated_at DESC
async def get_session(id: str) -> Optional[dict]  # SELECT *, 없으면 None
async def delete_session(id: str) -> None       # DELETE WHERE id = :id
async def update_session_title(id: str, title: str) -> None  # UPDATE SET title, updated_at = NOW()
```

---

## 5. 파일 구조

### 백엔드 (신규/수정)

```
ai_server/
├── api/
│   ├── schemas.py         ← SessionUpsertRequest, SessionSummary, SessionDetail, SessionTitleUpdate 추가
│   └── sessions.py        ← 신규: /api/sessions 라우터 (5개 엔드포인트)
│
├── repositories/
│   └── session_repo.py    ← 신규: upsert_session, list_sessions, get_session, delete_session, update_session_title
│
├── infra/
│   └── migrations/
│       └── 002_add_chat_sessions.sql  ← 신규 (참조용)
│
├── db/
│   └── init.sql           ← chat_sessions DDL 추가 (실제 적용)
│
└── server.py              ← sessions 라우터 include 추가
```

### 의존 방향

```
api/sessions.py → repositories/session_repo.py → infra/database.py
```

### 프런트엔드 (수정)

```
frontend/src/
├── api/
│   └── defectApi.js          ← fetchSessions, getSession, upsertSession, deleteSession, updateSessionTitle 추가
│
├── composables/
│   └── useDefectChat.js      ← localStorage → API 호출 교체
│
└── components/
    └── LeftPanel.vue         ← 더블클릭 인라인 제목 편집 UI 추가
```

---

## 6. 데이터 흐름

### 앱 초기화 (마운트 시)
```
useDefectChat 초기화
  → fetchSessions() 호출
  → GET /api/sessions
  → sessions.value = 응답 목록 (SessionSummary 배열)
  (실패 시: sessions.value = [], error에 메시지 표시 없이 조용히 처리)
```

### 세션 저장 (saveCurrentSession)
```
에이전트 완료 / 폴링 완료 후 saveCurrentSession() 호출
  → title 자동 생성 규칙 (최초 저장 시에만, 이후 PATCH로만 변경):
      const base = hypothesis ? hypothesis.slice(0, 30) : defectDescription.slice(0, 30)
      title = `${productId || 'Unknown'} — ${base || '새 분석'}`
    (sessions.value에서 기존 title 있으면 유지)
  → upsertSession(id, payload) 호출
  → PUT /api/sessions/{id}
  → DB upsert (INSERT ON CONFLICT DO UPDATE SET ... updated_at = NOW())
  → sessions 목록 갱신 (반환된 SessionSummary로 해당 항목 교체 또는 맨 앞에 추가)
  (실패 시: error.value에 메시지 설정, 사용자에게 저장 실패 표시)
```

### 세션 불러오기 (loadSession)
```
LeftPanel 카드 클릭 → session.id emit
  → loadSession(sessionId) 호출
  → GET /api/sessions/{id}  ← 전체 데이터 포함 (SessionDetail)
  → 상태 복원 (현재 localStorage 방식과 동일)
  → longTermStatus === 'PENDING' && longTermTaskId 있으면 resumePollBgStatus() 재개
  (실패 시: error.value에 메시지 설정)
```

**LeftPanel emit 변경:**
- 기존: `$emit('load-session', session)` (전체 객체)
- 변경: `$emit('load-session', session.id)` (ID만)

### 세션 삭제 (deleteSession)
```
🗑 버튼 클릭
  → DELETE /api/sessions/{id}
  → sessions 목록에서 제거
  (실패 시: 목록에서 제거하지 않음, error 표시)
```

### 제목 편집
```
LeftPanel 카드 제목 더블클릭
  → 인라인 input 활성화 (현재 title 값으로 초기화)
  → Enter 또는 blur 시 PATCH /api/sessions/{id}/title
  → 성공 시 로컬 sessions 목록 title 업데이트
  → 실패 시 원래 title로 복원
```

---

## 7. 에러 처리 전략

| 상황 | 처리 |
|---|---|
| `fetchSessions()` 실패 (앱 초기화) | 빈 목록으로 초기화, 사용자에게 에러 표시 없음 |
| `saveCurrentSession()` 실패 | `error.value`에 메시지 설정, 저장 실패 안내 |
| `loadSession()` 실패 | `error.value`에 메시지 설정, 상태 변경 없음 |
| `deleteSession()` 실패 | `error.value`에 메시지, 목록에서 제거 안 함 |
| `updateSessionTitle()` 실패 | 원래 title로 복원 |
| `PATCH /api/sessions/{id}/title` 404 | 목록에서 해당 항목 제거 (서버에서 삭제된 것으로 간주), error 표시 |
| `GET /api/sessions/{id}` 404 | 목록에서 해당 항목 제거, error 표시 |

---

## 8. 변경 범위 요약

| 파일 | 변경 유형 | 비고 |
|---|---|---|
| `db/init.sql` | 수정 | chat_sessions DDL 추가 |
| `infra/migrations/002_add_chat_sessions.sql` | 신규 | 참조용 |
| `repositories/session_repo.py` | 신규 | 세션 CRUD SQL (5개 함수) |
| `api/schemas.py` | 수정 | 세션 모델 4개 추가 |
| `api/sessions.py` | 신규 | 세션 라우터 5개 엔드포인트 |
| `server.py` | 수정 | sessions 라우터 include |
| `frontend/src/api/defectApi.js` | 수정 | 세션 API 함수 5개 추가 |
| `frontend/src/composables/useDefectChat.js` | 수정 | localStorage → API 교체, loadSession signature 변경 |
| `frontend/src/components/LeftPanel.vue` | 수정 | emit id만, 인라인 제목 편집 UI |

---

## 9. 성공 기준

- 앱 마운트 시 DB에서 세션 목록 로드
- 에이전트 완료/폴링 완료 후 자동으로 DB에 저장 (updated_at 갱신 포함)
- 세션 카드 클릭 시 DB에서 전체 데이터 복원, 폴링 재개
- 세션 삭제 시 DB에서 제거
- 세션 제목 더블클릭 수정 가능, 실패 시 원복
- localStorage 세션 관련 코드 완전 제거
- 기존 채팅/에이전트 실행 기능 동작 그대로 유지
- `GET /api/sessions/{id}` 404 시 목록에서 해당 항목 제거
