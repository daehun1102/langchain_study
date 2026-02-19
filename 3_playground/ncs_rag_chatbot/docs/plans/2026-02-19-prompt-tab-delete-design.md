# NCS RAG Chatbot — 프롬프트 관리 / 탭 UI / 삭제 일관성 설계

**작성일:** 2026-02-19
**상태:** 승인됨

---

## 개요

기존 아키텍처(`2026-02-19-architecture-migration-design.md`) 위에 세 가지 개선을 추가한다.

1. **Redis 초기 프롬프트 5개 등록** — agent 동작 지침을 역할별로 분리하여 Redis에 관리
2. **문서 삭제 일관성** — Oracle + PGVector + 파일 동시 삭제로 데이터 정합성 보장
3. **프론트엔드 탭 UI** — 대화 탭과 문서 관리 탭을 상단 탭 바로 분리

---

## 1. Redis 초기 프롬프트 5개

### 1.1 프롬프트 목록

| Key | 역할 |
|-----|------|
| `agent_system_prompt` | 에이전트 기본 페르소나 및 retrieve_context 사용 지침 |
| `answer_format_prompt` | 마크다운 답변 형식, 출처 언급, 불확실한 내용 처리 방법 |
| `no_document_prompt` | 관련 문서를 찾지 못했을 때 사용자에게 안내할 문구 |
| `query_enhance_prompt` | 검색 쿼리 구체화 지침 (NCS 문맥에 맞게, 다중 검색 허용) |
| `category_hint_prompt` | 카테고리 미선택 전체 검색 시 필터 안내 문구 |

### 1.2 통합 방식 (Approach A)

`agent.py`에 `_build_system_prompt()` 함수를 추가하여 5개를 순서대로 결합한다.

```python
def _build_system_prompt() -> str:
    keys = [
        "agent_system_prompt",
        "answer_format_prompt",
        "no_document_prompt",
        "query_enhance_prompt",
        "category_hint_prompt",
    ]
    return "\n\n".join(p for k in keys if (p := get_prompt(k)))

class ChatAgent:
    def __init__(self, model_name="gpt-4o-mini", system_prompt=None):
        self.model = init_chat_model(model_name)
        self.system_prompt = system_prompt if system_prompt is not None else _build_system_prompt()
```

### 1.3 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/init_prompts.py` | 5개 프롬프트 Redis 등록 (기존 1개 → 5개) |
| `src/prompt_loader.py` | 5개 fallback 값 추가 |
| `src/agent.py` | `_build_system_prompt()` 함수 추가, `__init__` 수정 |

---

## 2. 문서 삭제 일관성 (역제안)

### 2.1 문제점

현재 `DocumentService.delete(docId)` → Oracle만 삭제.
PGVector의 벡터 청크가 잔류하여 삭제된 문서의 내용이 검색 결과에 혼입될 수 있음.

### 2.2 해결 흐름

```
DELETE /api/documents/{docId}
  │
  ├─ Spring DocumentService
  │    ├─ 1. Python DELETE /internal/delete/{docId} 호출
  │    │      └─ Python: vector_store.delete_by_doc_id(docId)
  │    │           → PGVector에서 doc_id 일치 청크 전부 삭제
  │    ├─ 2. Oracle documents 테이블 삭제
  │    └─ 3. 로컬 파일(uploads/{docId}_*.pdf) 삭제
```

Python 호출 실패 시: 로그 경고 후 Oracle/파일 삭제는 진행 (best-effort).

### 2.3 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/vector_store.py` | `delete_by_doc_id(doc_id: str)` 메서드 추가 |
| `src/server.py` | `DELETE /internal/delete/{doc_id}` 엔드포인트 추가 |
| `backend/.../service/DocumentService.java` | `delete()` 에 Python 호출 + 파일 삭제 추가 |

---

## 3. 프론트엔드 탭 UI

### 3.1 레이아웃

```
┌──[대화]──[문서 관리]────────────────────────────┐
│                                                  │
│  [Chat 탭 활성]                                  │
│  ┌──FilterPanel──┬──────────ChatView──────────┐  │
│  │ NCS 카테고리   │  대화 메시지 목록           │  │
│  │ (접이식)       │  ...                       │  │
│  │               │  [입력창] [전송]             │  │
│  └───────────────┴────────────────────────────┘  │
│                                                  │
│  [문서 관리 탭 활성]                              │
│  ┌─────────────────────────────────────────────┐ │
│  │ PDF 업로드                                   │ │
│  │ [파일 선택] [메인▼] [서브▼] [등록 버튼]       │ │
│  ├─────────────────────────────────────────────┤ │
│  │ 등록된 문서 목록                              │ │
│  │ 파일명 | 카테고리 | [●INDEXED] | [삭제]       │ │
│  │ ...                                         │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### 3.2 상태 배지

| 상태 | 색상 | 의미 |
|------|------|------|
| `INDEXED` | 녹색 (`#4ade80`) | 벡터화 완료, 검색 가능 |
| `PENDING` | 노란색 (`#facc15`) | 업로드 완료, 벡터화 진행 중 |
| `FAILED` | 빨간색 (`#f87171`) | 벡터화 실패 |

### 3.3 수정/신규 파일

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/App.vue` | 상단 탭 바 (`대화` / `문서 관리`) 추가, `activeTab` 상태 관리 |
| `frontend/src/components/DocumentView.vue` | **신규** — 업로드 폼, 문서 목록, 삭제 버튼 |
| `frontend/src/api/ncsApi.js` | `uploadDocument()`, `fetchDocuments()`, `deleteDocument()` 추가 |

---

## 4. 구현 순서 (의존 관계)

```
Task A: Redis 5 prompts
  A1. src/init_prompts.py — 5개 등록
  A2. src/prompt_loader.py — fallback 5개 추가
  A3. src/agent.py — _build_system_prompt() 추가

Task B: 삭제 일관성 (Python)
  B1. src/vector_store.py — delete_by_doc_id()
  B2. src/server.py — DELETE /internal/delete/{doc_id}

Task C: 삭제 일관성 (Spring)  [B2 완료 후]
  C1. backend/.../service/DocumentService.java — delete() 수정

Task D: 프론트엔드 탭
  D1. frontend/src/api/ncsApi.js — API 메서드 추가
  D2. frontend/src/components/DocumentView.vue — 신규
  D3. frontend/src/App.vue — 탭 바 추가

A, B는 독립 병렬 가능
C는 B2 완료 후
D는 독립 진행 가능
```

---

## 5. 수정 파일 전체 목록

### Python (src/)
- `src/init_prompts.py`
- `src/prompt_loader.py`
- `src/agent.py`
- `src/vector_store.py`
- `src/server.py`

### Spring (backend/)
- `backend/src/main/java/com/ncs/backend/service/DocumentService.java`

### Frontend (frontend/)
- `frontend/src/App.vue`
- `frontend/src/components/DocumentView.vue` (신규)
- `frontend/src/api/ncsApi.js`
