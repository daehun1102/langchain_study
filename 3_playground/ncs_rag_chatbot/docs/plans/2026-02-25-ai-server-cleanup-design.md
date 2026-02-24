# ai_server 루트 정리 설계

**Goal:** ai_server 루트의 shim 파일 삭제 및 파이프라인 파일을 infra/로 이동하여 구조를 단순화한다.

---

## 현재 문제

`ai_server/` 루트에 역할이 다른 파일들이 혼재:
- **shim 파일 6개** — 이전 리팩토링 과정에서 하위호환을 위해 남긴 1줄짜리 re-export 래퍼 (`agent.py`, `embeddings.py`, `tool.py`, `vector_store.py`, `prompt_loader.py`, `tracing.py`)
- **파이프라인 파일 3개** — PDF 적재 관련 모듈이 루트에 방치 (`loader.py`, `splitter.py`, `ingest.py`)
- **초기화 스크립트** — 운영 스크립트가 루트에 방치 (`init_prompts.py`)

---

## 결정 사항

**Approach A** 채택: shim 삭제 + 파이프라인/스크립트 파일을 각각 `infra/`, `scripts/`로 이동

---

## 목표 구조

```
ai_server/
  server.py           ← FastAPI 진입점 (유지)
  config.py           ← 환경변수 설정 (유지)
  pytest.ini          ← 테스트 설정 (유지)
  requirements.txt    ← 의존성 (유지)

  agents/             ← 에이전트 (변경 없음)
    base.py
    v1/
      rag_agent.py
      sql_agent.py
      supervisor.py

  clients/            ← HTTP 클라이언트 (변경 없음)
    spring/
      base.py
      v1/employee.py

  eval/               ← 평가 모듈 (변경 없음, tasks.py import만 수정)
    configs.py, create_dataset.py, evaluators.py
    run_evaluation.py, tasks.py
    tests/

  infra/              ← 인프라 (기존 + 신규 이동)
    embeddings.py       ← 기존
    vector_store.py     ← 기존
    prompt_loader.py    ← 기존
    tracing.py          ← 기존
    loader.py           ← 루트에서 이동
    splitter.py         ← 루트에서 이동
    ingest.py           ← 루트에서 이동

  scripts/            ← 운영 스크립트 (신규 디렉토리)
    __init__.py
    init_prompts.py     ← 루트에서 이동

  tests/              ← 유닛 테스트 (변경 없음)
  tools/              ← 도구 (변경 없음)
```

---

## 삭제 대상 (shim 6개)

| 파일 | 내용 | 삭제 이유 |
|------|------|-----------|
| `agent.py` | `from agents.v1.rag_agent import ...` | eval/tasks.py 직접 import로 대체 |
| `embeddings.py` | `from infra.embeddings import ...` | eval/tasks.py 직접 import로 대체 |
| `tool.py` | `from tools.rag_tool import ...` | eval/tasks.py 직접 import로 대체 |
| `vector_store.py` | `from infra.vector_store import ...` | eval/tasks.py 직접 import로 대체 |
| `prompt_loader.py` | `from infra.prompt_loader import ...` | eval/tasks.py 직접 import로 대체 |
| `tracing.py` | `from infra.tracing import ...` | 미사용 shim |

---

## 수정이 필요한 파일

| 파일 | 변경 내용 |
|------|-----------|
| `eval/tasks.py` | shim → 실제 경로로 직접 import |
| `infra/ingest.py` | `from loader` → `from infra.loader`, `from splitter` → `from infra.splitter`, `from embeddings` → `from infra.embeddings` |
| `server.py` | `from ingest` → `from infra.ingest` |
| `infra/__init__.py` | `loader`, `splitter`, `ingest` export 추가 (선택) |

---

## 테스트 전략

- 각 파일 이동/삭제 후 `pytest eval/tests/ tests/ -v` 로 전체 테스트 PASS 확인
- 최종적으로 서버 임포트 오류 없음 확인 (`python -c "import server"`)
