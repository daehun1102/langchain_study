# src → ai_server 디렉토리 리네임 설계

**작성일:** 2026-02-20
**상태:** 승인됨

---

## 개요

Python AI 서버 모듈 디렉토리를 `src/`에서 `ai_server/`로 변경하여
프로젝트 구조를 더 명확하게 표현한다.

## 변경 범위

| 파일 | 변경 내용 |
|------|-----------|
| `src/` 디렉토리 | `ai_server/`로 git mv |
| `server.py` L22 | `sys.path.insert(0, "src")` → `"ai_server"` |
| `ai_server/init_prompts.py` 주석 | `python src/init_prompts.py` → `python ai_server/init_prompts.py` |
| `README.md` | 디렉토리 구조 표기 업데이트 |

## 변경 제외

- `venv/` 내부 파일 — 외부 라이브러리, 무관
- `SPEC.md`, `docs/plans/*.md` — 완료된 구현 기록, 유지

## 결과 디렉토리 구조

```
ncs_rag_chatbot/
├── ai_server/          ← (구 src/) Python AI 모듈
│   ├── agent.py
│   ├── embeddings.py
│   ├── ingest.py
│   ├── init_prompts.py
│   ├── loader.py
│   ├── main.py
│   ├── prompt_loader.py
│   ├── splitter.py
│   ├── tool.py
│   ├── tracing.py
│   └── vector_store.py
├── server.py           ← FastAPI 진입점
├── backend/            ← Spring Boot API Gateway
└── frontend/           ← Vue 3
```

## 서버 실행 명령어 (변경 없음)

```bash
uvicorn server:app --reload --port 8000
```
