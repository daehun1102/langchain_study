# server.py → ai_server/ 이동 설계

**날짜**: 2026-02-23
**목적**: Python 서버 진입점을 ai_server/ 안으로 이동하여 비정상적인 `sys.path` 해킹 제거

---

## 문제

`server.py`가 프로젝트 루트에 위치하고, `ai_server/` 모듈들을 `sys.path.insert`로 우회 임포트한다.

```python
# server.py (루트) — 현재
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ai_server"))
from agent import ChatAgent   # 해킹으로 동작하는 임포트
```

추가로 `ai_server/main.py`가 진입점처럼 보이지만 실제로는 사용하지 않는 유물 파일이다.

---

## 해결 방향

**Approach A — Minimal Move** 채택.

- `server.py` → `ai_server/server.py`로 이동
- `sys.path.insert` 1줄 삭제
- `ai_server/main.py` 삭제 (미사용 유물)
- README, docstring의 실행 명령 업데이트

임포트 변경 없음. eval/ 패턴과 동일하게 `ai_server/` 내에서 uvicorn 실행.

---

## 변경 명세

| 파일 | 변경 |
|------|------|
| `server.py` (루트) | `ai_server/server.py`로 git mv |
| `ai_server/server.py` | `sys.path.insert(0, ...)` 삭제, docstring 업데이트 |
| `ai_server/main.py` | 삭제 |
| `README.md` | Python 서버 실행 명령 업데이트 |

---

## Side Effect가 없는 이유

uvicorn을 `ai_server/` 내에서 실행하면 Python이 CWD를 `sys.path[0]`에 자동 추가한다.
`from agent import ChatAgent` 등 기존 flat import가 그대로 동작한다.

이는 eval 시스템(`cd ai_server && python -m eval.run_evaluation`)과 동일한 패턴이다.

---

## 새 실행 명령

```bash
# 변경 전
uvicorn server:app --reload --port 8000

# 변경 후
cd ai_server
uvicorn server:app --reload --port 8000
```

---

## 최종 구조

```
ncs_rag_chatbot/
├── ai_server/
│   ├── server.py       ← 이동 (FastAPI 앱 진입점)
│   ├── agent.py
│   ├── embeddings.py
│   ├── vector_store.py
│   ├── tool.py
│   ├── ingest.py
│   ├── tracing.py
│   ├── prompt_loader.py
│   ├── loader.py
│   ├── splitter.py
│   ├── requirements.txt
│   └── eval/
├── backend/
├── frontend/
└── README.md
```
