# AI Server 리팩토링 설계

**날짜:** 2026-02-27
**범위:** `ai_server/` Python 코드
**접근:** 균형 리팩토링 — 중복 제거, 설정 일관성, ingest 개선

---

## 목표

1. 4개 에이전트에 복붙된 `run()` 메서드를 `BaseAgent`로 이동
2. 설정 값 불일치(`ChatAgent` 모델명 하드코딩, `TABLE_NAME` 중복, 미사용 `agent_version`) 정리
3. `ingest_single_document()`가 서버의 `VectorStoreManager`를 재사용하도록 개선

---

## 섹션 1: BaseAgent run() 이동

### 현황
`v1/rag_agent.py`, `v1/sql_agent.py`, `v1/supervisor.py`, `v2/supervisor.py` 4개 파일에 완전히 동일한 `run()` 구현이 복붙되어 있다.

### 변경
- `agents/base.py`: `self.agent = None` 초기화 + `run()` 기본 구현 추가
- `hasattr(self, "agent")` 체크 → `self.agent is None` 체크로 교체
- 자식 4개 클래스에서 `run()` 메서드 삭제

### 영향 범위
- `agents/base.py` 수정
- `agents/v1/rag_agent.py`, `agents/v1/sql_agent.py`, `agents/v1/supervisor.py`, `agents/v2/supervisor.py` — `run()` 삭제 및 `self.agent = None` 추가
- **테스트 무수정** (인터페이스 변경 없음)

---

## 섹션 2: 설정 일관성 정리

### 2-1. ChatAgent 모델명 하드코딩 제거
- **파일:** `agents/v1/rag_agent.py:33`
- **Before:** `def __init__(self, model_name: str = "gpt-4o-mini", ...)`
- **After:** `def __init__(self, model_name: str = None, ...)` + `init_chat_model(model_name or settings.model_name)`
- `from config import settings` import 추가

### 2-2. TABLE_NAME 단일 소스화
- **단일 소스:** `infra/vector_store.py` (그대로 유지)
- **변경:** `infra/ingest.py`에서 `TABLE_NAME` 상수 정의 삭제, `from infra.vector_store import TABLE_NAME` import로 교체
- `VECTOR_SIZE`, `METADATA_COLUMNS`는 `ingest.py` 고유 상수이므로 유지

### 2-3. 미사용 settings.agent_version 삭제
- **파일:** `config.py`
- `agent_version: str = "v1"` 줄 삭제
- 코드베이스 전체에서 참조 없음 확인됨

---

## 섹션 3: ingest_single_document 개선

### 현황
`server.py`의 `/internal/ingest` 엔드포인트가 `ingest_single_document(doc_id, file_path, db_connection)`을 호출하면, 함수 내부에서 DB 엔진과 벡터스토어를 새로 생성한다. 서버는 이미 `VectorStoreManager`를 전역으로 유지하고 있어 커넥션이 중복된다.

### 변경
```python
# infra/ingest.py
async def ingest_single_document(
    doc_id: str,
    file_path: str,
    db_connection: str | None = None,
    vsm=None,  # VectorStoreManager | None
) -> int:
    if vsm is not None:
        vector_store = vsm.get_vector_store()
    else:
        # CLI 실행 시 기존처럼 자체 생성
        embedding_model = EmbeddingModel().get_embeddings()
        pg_engine = await _get_pg_engine(db_connection)
        vector_store = await _get_vector_store(pg_engine, embedding_model)
    ...
```

- `server.py`의 `ingest()` 핸들러: `vsm=vector_store_manager` 추가 전달
- CLI(`__main__`) 경로: 기존 `db_connection` 방식 그대로 유지

---

## 파일 변경 요약

| 파일 | 변경 내용 |
|------|-----------|
| `agents/base.py` | `self.agent = None` 초기화 + `run()` 기본 구현 추가 |
| `agents/v1/rag_agent.py` | `run()` 삭제, `self.agent = None` 추가, 모델명 `settings.model_name` 통일 |
| `agents/v1/sql_agent.py` | `run()` 삭제, `self.agent = None` 추가 |
| `agents/v1/supervisor.py` | `run()` 삭제, `self.agent = None` 추가 |
| `agents/v2/supervisor.py` | `run()` 삭제, `self.agent = None` 추가 |
| `config.py` | `agent_version` 필드 삭제 |
| `infra/vector_store.py` | 변경 없음 (TABLE_NAME 단일 소스 역할 유지) |
| `infra/ingest.py` | `TABLE_NAME` 자체 정의 삭제 → import, `vsm` 파라미터 추가 |
| `server.py` | `ingest()` 핸들러에 `vsm=vector_store_manager` 전달 |
