# 프롬프트 관리 개선 및 Redis Fallback 제거 설계

**Date:** 2026-02-23
**Scope:** `ai_server/prompt_loader.py`, `ai_server/agent.py`, `ai_server/init_prompts.py`

---

## 목표

1. Redis에서 프롬프트를 가져오지 못할 경우 fallback 데이터 대신 예외를 발생시킨다.
2. `init_prompts.py`를 삭제하고 프롬프트 초기값 등록은 Spring `PUT /api/prompts/{key}` API로만 수행한다.
3. Redis 연결을 모듈 레벨에서 한 번만 생성하여 connection pool을 재사용한다.

---

## 변경 범위

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `ai_server/prompt_loader.py` | 수정 | 전면 재설계 |
| `ai_server/agent.py` | 수정 | exception handler 추가 |
| `ai_server/init_prompts.py` | 삭제 | Spring API로 대체 |

---

## 설계

### 1. `PromptLoadError` 커스텀 예외

`prompt_loader.py`에 정의한다. Redis 관련 모든 실패를 이 예외로 통일한다.

```python
class PromptLoadError(Exception):
    pass
```

### 2. `prompt_loader.py` 재설계

**제거:**
- `FALLBACK_PROMPTS` 딕셔너리 전체

**추가:**
- 모듈 레벨 `_redis` 인스턴스 (connection pool 재사용)
- `PromptLoadError` 예외 클래스

**`get_prompt()` 동작:**
- Redis 연결 실패 → `PromptLoadError("Redis 연결 실패: {e}")` raise
- 키가 Redis에 없음(None) → `PromptLoadError("프롬프트 키 없음: 'prompt:{key}'")`  raise
- 성공 → value 반환

```python
_redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def get_prompt(key: str) -> str:
    try:
        value = _redis.get(PREFIX + key)
    except redis.RedisError as e:
        raise PromptLoadError(f"Redis 연결 실패: {e}") from e

    if value is None:
        raise PromptLoadError(f"프롬프트 키 없음: '{PREFIX + key}'")

    return value
```

### 3. `agent.py` 변경

**`_build_system_prompt()`:**
- `PromptLoadError`를 잡지 않고 그대로 전파
- 빈 문자열 필터링(`if p`) 제거 — 모든 키는 Redis에 반드시 존재해야 함

```python
def _build_system_prompt() -> str:
    parts = [get_prompt(k) for k in PROMPT_KEYS]
    return "\n\n".join(parts)
```

**FastAPI exception handler 추가:**
- `PromptLoadError` → HTTP 503 응답
- 그 외 예외 → 기존 500 처리 유지

```python
@app.exception_handler(PromptLoadError)
async def prompt_load_error_handler(request, exc):
    return JSONResponse(
        status_code=503,
        content={"error": "프롬프트 로드 실패", "detail": str(exc)},
    )
```

### 4. `init_prompts.py` 삭제

프롬프트 초기값 등록은 Spring Boot의 `PUT /api/prompts/{key}` 엔드포인트를 사용한다.

```bash
# 예시: agent_system_prompt 등록
curl -X PUT http://localhost:8080/api/prompts/agent_system_prompt \
  -H "Content-Type: application/json" \
  -d '{"value": "너는 NCS 문서에서 정보를 검색하여 답변해주는 AI 어시스턴트야..."}'
```

---

## 호출 흐름

```
POST /internal/chat
  → ChatAgent()
    → _build_system_prompt()
      → get_prompt("agent_system_prompt")
        ✗ Redis 다운  → PromptLoadError → 503 {"error": "프롬프트 로드 실패", "detail": "Redis 연결 실패: ..."}
        ✗ 키 없음    → PromptLoadError → 503 {"error": "프롬프트 로드 실패", "detail": "프롬프트 키 없음: 'prompt:agent_system_prompt'"}
        ✓ 성공       → 정상 진행
```

---

## 정책 결정 사항

| 항목 | 결정 |
|------|------|
| Redis 실패 시 동작 | 예외 발생 (요청 실패), fallback 없음 |
| 프롬프트 초기화 방법 | Spring API (`PUT /api/prompts/{key}`) |
| Redis 연결 방식 | 모듈 레벨 단일 인스턴스 (connection pool 재사용) |
| HTTP 에러 코드 | 503 Service Unavailable |
