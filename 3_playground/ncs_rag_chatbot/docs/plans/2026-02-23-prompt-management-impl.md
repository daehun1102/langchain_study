# 프롬프트 관리 개선 및 Redis Fallback 제거 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `prompt_loader.py`에서 fallback 딕셔너리를 제거하고, Redis 실패 시 `PromptLoadError`(503)를 발생시키도록 개선한다.

**Architecture:** 모듈 레벨 Redis 인스턴스를 재사용하고, 커스텀 예외 `PromptLoadError`를 정의한다. FastAPI exception handler가 이를 503으로 변환한다. `init_prompts.py`는 삭제하며 프롬프트 초기화는 Spring API로만 수행한다.

**Tech Stack:** Python 3.10+, redis-py, FastAPI, pytest, unittest.mock

---

## Task 1: `init_prompts.py` 삭제

**Files:**
- Delete: `ai_server/init_prompts.py`

**Step 1: 파일 삭제**

```bash
git rm ai_server/init_prompts.py
```

**Step 2: 삭제 확인**

```bash
ls ai_server/init_prompts.py
```

Expected: `No such file or directory`

**Step 3: Commit**

```bash
git commit -m "remove(python): init_prompts.py 삭제 - 프롬프트 초기화는 Spring API로 대체"
```

---

## Task 2: `prompt_loader.py` 재설계

**Files:**
- Test: `ai_server/eval/tests/test_prompt_loader.py` (신규)
- Modify: `ai_server/prompt_loader.py`

### Step 1: 테스트 파일 작성

`ai_server/eval/tests/test_prompt_loader.py`:

```python
"""
test_prompt_loader.py — prompt_loader 단위 테스트

conftest.py가 redis를 MagicMock으로 패치하므로,
각 테스트에서 prompt_loader._redis를 직접 패치하여 동작을 제어한다.
"""

import pytest
from unittest.mock import MagicMock, patch
import prompt_loader
from prompt_loader import get_prompt, PromptLoadError


def test_get_prompt_success():
    """Redis에서 값을 정상적으로 가져오면 그 값을 반환한다."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = "테스트 프롬프트"

    with patch.object(prompt_loader, "_redis", mock_redis):
        result = get_prompt("agent_system_prompt")

    assert result == "테스트 프롬프트"
    mock_redis.get.assert_called_once_with("prompt:agent_system_prompt")


def test_get_prompt_raises_on_missing_key():
    """Redis에 키가 없으면 (None 반환) PromptLoadError를 발생시킨다."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    with patch.object(prompt_loader, "_redis", mock_redis):
        with pytest.raises(PromptLoadError, match="프롬프트 키 없음: 'prompt:missing_key'"):
            get_prompt("missing_key")


def test_get_prompt_raises_on_connection_error():
    """Redis 연결 실패 시 PromptLoadError를 발생시킨다."""
    mock_redis = MagicMock()
    mock_redis.get.side_effect = Exception("Connection refused")

    with patch.object(prompt_loader, "_redis", mock_redis):
        with pytest.raises(PromptLoadError, match="Redis 연결 실패"):
            get_prompt("agent_system_prompt")


def test_prompt_load_error_is_exception():
    """PromptLoadError가 Exception을 상속한다."""
    assert issubclass(PromptLoadError, Exception)
```

**Step 2: 테스트 실행 — 실패 확인**

```bash
cd ai_server && python -m pytest eval/tests/test_prompt_loader.py -v
```

Expected: `ImportError` 또는 `AttributeError` — `PromptLoadError`가 아직 없으므로 실패

**Step 3: `prompt_loader.py` 전체 교체**

`ai_server/prompt_loader.py`:

```python
"""
prompt_loader.py — Redis에서 프롬프트 템플릿을 로드하는 모듈

Spring의 PromptService가 저장한 "prompt:<key>" 형식의 키를 읽는다.
Redis 연결 실패 또는 키가 없으면 PromptLoadError를 발생시킨다.
"""

import os
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
PREFIX = "prompt:"

# 모듈 레벨에서 한 번만 생성 — redis-py 내부 connection pool 재사용
_redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


class PromptLoadError(Exception):
    """Redis에서 프롬프트를 로드하지 못했을 때 발생하는 예외."""
    pass


def get_prompt(key: str) -> str:
    """Redis에서 프롬프트를 가져온다.

    Args:
        key: 프롬프트 키 (PREFIX 제외). 예: "agent_system_prompt"

    Returns:
        Redis에 저장된 프롬프트 문자열

    Raises:
        PromptLoadError: Redis 연결 실패 또는 키가 존재하지 않을 때
    """
    try:
        value = _redis.get(PREFIX + key)
    except Exception as e:
        raise PromptLoadError(f"Redis 연결 실패: {e}") from e

    if value is None:
        raise PromptLoadError(f"프롬프트 키 없음: '{PREFIX + key}'")

    return value
```

**Step 4: 테스트 실행 — 통과 확인**

```bash
cd ai_server && python -m pytest eval/tests/test_prompt_loader.py -v
```

Expected:
```
PASSED test_get_prompt_success
PASSED test_get_prompt_raises_on_missing_key
PASSED test_get_prompt_raises_on_connection_error
PASSED test_prompt_load_error_is_exception
```

**Step 5: Commit**

```bash
git add ai_server/prompt_loader.py ai_server/eval/tests/test_prompt_loader.py
git commit -m "feat(python): PromptLoadError 도입, Redis fallback 제거, 모듈 레벨 연결 풀 사용"
```

---

## Task 3: `agent.py` 빈 문자열 필터 제거

**Files:**
- Modify: `ai_server/agent.py`

**Step 1: 변경 전 동작 이해**

현재 `_build_system_prompt()`는 아래처럼 빈 문자열을 필터링한다:

```python
# 현재 코드 (ai_server/agent.py:34)
parts = [p for k in PROMPT_KEYS if (p := get_prompt(k))]
```

이제 `get_prompt()`는 빈 문자열 대신 `PromptLoadError`를 발생시키므로, 이 필터는 불필요하다.

**Step 2: `agent.py` 수정**

`ai_server/agent.py`의 `_build_system_prompt()` 함수를 아래로 교체:

```python
def _build_system_prompt() -> str:
    """Redis에서 5개 프롬프트를 로드하여 하나의 system prompt로 결합한다.

    Redis에서 키를 찾지 못하면 PromptLoadError를 발생시킨다.
    """
    parts = [get_prompt(k) for k in PROMPT_KEYS]
    return "\n\n".join(parts)
```

또한 docstring 상단의 "Redis 연결 실패 시 fallback 값을 사용한다" 문구를 삭제한다:

```python
"""
agent.py — LangChain/LangGraph 기반 채팅 에이전트

Phase 3 변경:
- 하드코딩 시스템 프롬프트 제거
- Redis에서 프롬프트 로드 (prompt_loader.get_prompt)

Phase 3.1 변경:
- _build_system_prompt(): 5개 프롬프트를 결합하여 단일 system_prompt 생성
"""
```

**Step 3: Commit**

```bash
git add ai_server/agent.py
git commit -m "refactor(python): _build_system_prompt에서 빈 문자열 필터 제거"
```

---

## Task 4: `server.py`에 PromptLoadError exception handler 추가

**Files:**
- Modify: `ai_server/server.py`

**Step 1: import 추가**

`ai_server/server.py`의 기존 import 블록에 추가:

```python
from fastapi.responses import JSONResponse
from prompt_loader import PromptLoadError
```

**Step 2: exception handler 추가**

`app = FastAPI(...)` 정의 바로 아래에 추가:

```python
@app.exception_handler(PromptLoadError)
async def prompt_load_error_handler(request, exc):
    """Redis 프롬프트 로드 실패 시 503 응답을 반환한다."""
    logger.error("[prompt] 프롬프트 로드 실패: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"error": "프롬프트 로드 실패", "detail": str(exc)},
    )
```

**Step 3: 서버 기동 후 동작 확인**

Redis가 내려간 상태에서 채팅 요청을 보내면 503이 반환되어야 한다.

```bash
# Redis 중지 (테스트용)
# docker stop redis

curl -X POST http://localhost:8000/internal/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "테스트", "doc_ids": []}'
```

Expected:
```json
{
  "error": "프롬프트 로드 실패",
  "detail": "Redis 연결 실패: ..."
}
```
HTTP Status: `503 Service Unavailable`

Redis에 키가 없을 때:

```json
{
  "error": "프롬프트 로드 실패",
  "detail": "프롬프트 키 없음: 'prompt:agent_system_prompt'"
}
```

**Step 4: Commit**

```bash
git add ai_server/server.py
git commit -m "feat(python): PromptLoadError → 503 exception handler 추가"
```

---

## Task 5: 전체 테스트 통과 확인

**Step 1: 전체 테스트 실행**

```bash
cd ai_server && python -m pytest eval/tests/ -v
```

Expected: 모든 테스트 PASSED

**Step 2: 프롬프트 정상 로드 확인 (Redis 기동 상태에서)**

```bash
# Redis에 필수 프롬프트 등록 (Spring API 또는 redis-cli)
redis-cli set "prompt:agent_system_prompt" "너는 NCS 문서에서 정보를 검색하여 답변해주는 AI 어시스턴트야."
redis-cli set "prompt:answer_format_prompt" "답변 형식 지침: 마크다운 형식으로 작성해줘."
redis-cli set "prompt:no_document_prompt" "관련 문서를 찾지 못했을 때 안내: 관련 내용을 찾을 수 없습니다."
redis-cli set "prompt:query_enhance_prompt" "검색 쿼리 최적화 지침: 사용자 질의를 구체화하여 검색해줘."
redis-cli set "prompt:category_hint_prompt" "카테고리 안내: 카테고리를 선택하면 더 정확한 답변을 받을 수 있습니다."
```

```bash
# 정상 응답 확인
curl -X POST http://localhost:8000/internal/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "NCS란 무엇인가요?", "doc_ids": []}'
```

Expected: HTTP 200, `{"answer": "...", "sources": [...]}`

**Step 3: 최종 Commit (필요 시)**

```bash
git add .
git commit -m "test: 프롬프트 관리 개선 전체 검증 완료"
```

---

## 변경 요약

| 파일 | 변경 내용 |
|------|-----------|
| `ai_server/init_prompts.py` | 삭제 |
| `ai_server/prompt_loader.py` | `FALLBACK_PROMPTS` 제거, `PromptLoadError` 추가, 모듈 레벨 `_redis` 인스턴스 |
| `ai_server/agent.py` | `_build_system_prompt()` 빈 문자열 필터 제거 |
| `ai_server/server.py` | `PromptLoadError` exception handler 추가 |
| `ai_server/eval/tests/test_prompt_loader.py` | 신규 — 3개 예외 케이스 + 1개 성공 케이스 |
