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
- `title`: 사용자 수정 가능 이름. 기본값은 프런트에서 `{productId} — {hypothesis 앞 30자}`로 자동 생성.
- `agent_results`: `{ process_history, return_history, test_result, long_term }` 각각 `{ analysis, suspectRows }`.
- `chat_messages`: 에이전트 카드 + 사용자 채팅 메시지 배열.
- `long_term_task_id` + `long_term_status`: 세션 복원 시 폴링 재개에 필요.
- `final_action_plan`: 현재 localStorage에 누락된 필드. DB 저장으로 복원 가능하게 됨.

---

## 3. API 엔드포인트

리팩토링 설계(`2026-03-11-ai-server-refactor-design.md`)의 레이어 구조를 따름.
세션 CRUD는 비즈니스 로직 없이 단순 저장/조회이므로 서비스 레이어 없이 라우터에서 repository 직접 호출.

### 엔드포인트 목록

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/sessions` | 세션 목록 (최신순, 요약 정보만) |
| `PUT` | `/api/sessions/{id}` | 세션 upsert (전체 데이터 저장/업데이트) |
| `DELETE` | `/api/sessions/{id}` | 세션 삭제 |
| `PATCH` | `/api/sessions/{id}/title` | 제목만 업데이트 |

### Pydantic 모델 (`api/schemas.py`에 추가)

```python
class SessionUpsertRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    title: str
    product_id: str
    defect_description: str
    hypothesis: str
    agent_results: dict
    chat_messages: list
    enabled_agents: dict
    long_term_task_id: Optional[str] = None
    long_term_status: str
    long_term_result: Optional[str] = None
    final_action_plan: str

class SessionSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    title: str
    product_id: str
    hypothesis: str
    agent_results: dict   # LeftPanel의 ranAgents() 표시에 필요
    updated_at: str

class SessionTitleUpdate(BaseModel):
    title: str
```

### `GET /api/sessions` 응답 예시

```json
[
  {
    "id": "abc-123",
    "title": "LOT-A001 — 픽셀 전극 단락",
    "productId": "LOT-A001",
    "hypothesis": "픽셀 전극 단락으로 인한 Dead Pixel",
    "agentResults": { "process_history": {...}, ... },
    "updatedAt": "2026-03-11T10:30:00Z"
  }
]
```

---

## 4. 파일 구조

### 백엔드 (신규/수정)

```
ai_server/
├── api/
│   ├── schemas.py         ← SessionUpsertRequest, SessionSummary, SessionTitleUpdate 추가
│   └── sessions.py        ← 신규: /api/sessions 라우터
│
├── repositories/
│   └── session_repo.py    ← 신규: upsert_session, list_sessions, delete_session, update_session_title
│
├── infra/
│   └── migrations/
│       └── 002_add_chat_sessions.sql  ← 신규
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
│   └── defectApi.js          ← fetchSessions, upsertSession, deleteSession, updateSessionTitle 추가
│
├── composables/
│   └── useDefectChat.js      ← localStorage → API 호출 교체
│                                saveCurrentSession: PUT /api/sessions/{id}
│                                loadSession: GET 목록에서 전체 데이터 포함 or GET /api/sessions/{id}
│                                deleteSession: DELETE /api/sessions/{id}
│                                앱 초기화 시 fetchSessions() 호출
│
└── components/
    └── LeftPanel.vue         ← 더블클릭 인라인 제목 편집 UI 추가
                                 PATCH /api/sessions/{id}/title 호출
```

---

## 5. 데이터 흐름

### 앱 초기화 (마운트 시)
```
useDefectChat 초기화
  → fetchSessions() 호출
  → GET /api/sessions
  → sessions.value = 응답 목록
```

### 세션 저장 (saveCurrentSession)
```
에이전트 완료 / 폴링 완료 후 saveCurrentSession() 호출
  → title 자동 생성: `${productId} — ${hypothesis.slice(0, 30)}`
    (기존 title 있으면 유지)
  → upsertSession(id, payload) 호출
  → PUT /api/sessions/{id}
  → DB upsert (INSERT ON CONFLICT DO UPDATE)
  → sessions 목록 갱신 (응답으로 받은 summary로 교체)
```

### 세션 불러오기 (loadSession)
```
LeftPanel 카드 클릭
  → loadSession(sessionId) 호출
  → GET /api/sessions/{id}  ← 전체 데이터 포함 (chatMessages 등)
  → 상태 복원 (현재 localStorage 방식과 동일)
  → longTermStatus === 'PENDING' 이면 resumePollBgStatus() 재개
```

### 세션 삭제 (deleteSession)
```
🗑 버튼 클릭
  → DELETE /api/sessions/{id}
  → sessions 목록에서 제거
```

### 제목 편집
```
LeftPanel 카드 제목 더블클릭
  → 인라인 input 활성화
  → Enter / blur 시 PATCH /api/sessions/{id}/title
  → 로컬 sessions 목록 title 업데이트
```

---

## 6. 변경 범위 요약

| 파일 | 변경 유형 | 비고 |
|---|---|---|
| `infra/migrations/002_add_chat_sessions.sql` | 신규 | chat_sessions DDL |
| `repositories/session_repo.py` | 신규 | 세션 CRUD SQL |
| `api/schemas.py` | 수정 | 세션 모델 3개 추가 |
| `api/sessions.py` | 신규 | 세션 라우터 4개 엔드포인트 |
| `server.py` | 수정 | sessions 라우터 include |
| `frontend/src/api/defectApi.js` | 수정 | 세션 API 함수 4개 추가 |
| `frontend/src/composables/useDefectChat.js` | 수정 | localStorage → API 교체 |
| `frontend/src/components/LeftPanel.vue` | 수정 | 인라인 제목 편집 UI |

---

## 7. 성공 기준

- 앱 마운트 시 DB에서 세션 목록 로드
- 에이전트 완료/폴링 완료 후 자동으로 DB에 저장
- 세션 카드 클릭 시 DB에서 전체 데이터 복원, 폴링 재개
- 세션 삭제 시 DB에서 제거
- 세션 제목 더블클릭 수정 가능
- localStorage 세션 관련 코드 완전 제거
- 기존 채팅/에이전트 실행 기능 동작 그대로 유지
