# AgentKey Enum Registry Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 에이전트 식별자 문자열을 `AgentKey(StrEnum)`으로 중앙화하여, 에이전트 추가/rename 시 `registry.py` 한 파일만 수정하면 되도록 한다.

**Architecture:** `agents/registry.py`에 `AgentKey`와 `AGENT_NODE_MAP`을 정의하고, `state.py` / `graph.py` / `server.py`가 이를 import하여 raw string 대신 사용한다. `StrEnum`을 사용하므로 JSON 직렬화·API contract 변경 없이 기존과 호환된다.

**Tech Stack:** Python `enum.StrEnum` (Python 3.11+), LangGraph, FastAPI, pytest

---

## 변경 대상 파일 요약

| 파일 | 역할 |
|------|------|
| `agents/registry.py` (신규) | `AgentKey` enum, `AGENT_NODE_MAP` 정의. 유일한 SSoT. |
| `agents/state.py` | `Literal[...]` → `AgentKey`, `enabled_agents` 타입 갱신 |
| `agents/graph.py` | `_NODE_MAP`, `ALL_AGENTS` → registry 참조 |
| `server.py` | `ALL_AGENTS` import 유지 (변경 없음, 자동 반영) |
| `tests/test_agent_registry.py` (신규) | registry 단위 테스트 |

**변경하지 않는 파일:**
- `agents/sub/*.py` — node 함수 내부는 str 반환이므로 영향 없음
- `agents/prompts.py` — 프롬프트 텍스트는 사람이 읽는 설명이므로 그대로 유지
- `agents/synthesis_node.py` — state key 접근은 state.py 타입과 독립적
- `frontend/*` — JS 레이어는 별도 `AGENT_CONFIG` 유지 (API boundary)

---

## Chunk 1: AgentKey 정의 및 테스트

### Task 1: `agents/registry.py` 생성

**Files:**
- Create: `3_playground/display_defect_chatbot/ai_server/agents/registry.py`
- Create: `3_playground/display_defect_chatbot/tests/test_agent_registry.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_agent_registry.py`:
```python
# tests/test_agent_registry.py
from ai_server.agents.registry import AgentKey, AGENT_NODE_MAP


def test_agent_key_values():
    """AgentKey 값이 기존 API contract 문자열과 동일한지 검증"""
    assert AgentKey.PROCESS_HISTORY == "process_history"
    assert AgentKey.RETURN_HISTORY  == "return_history"
    assert AgentKey.TEST_HISTORY    == "test_history"
    assert AgentKey.LONG_TERM       == "long_term"


def test_agent_key_is_str():
    """StrEnum이므로 isinstance(key, str) == True — JSON 직렬화 호환"""
    for key in AgentKey:
        assert isinstance(key, str), f"{key} is not a str"


def test_agent_node_map_covers_all_keys():
    """AGENT_NODE_MAP이 모든 AgentKey를 커버하는지 검증"""
    assert set(AGENT_NODE_MAP.keys()) == set(AgentKey)


def test_agent_node_map_node_names():
    """노드 이름이 기존 규칙({key}_node)을 따르는지 검증"""
    for key, node_name in AGENT_NODE_MAP.items():
        assert node_name == f"{key}_node", f"{key} → {node_name} 형식 불일치"
```

- [ ] **Step 2: 테스트 실행 — FAIL 확인**

```bash
cd 3_playground/display_defect_chatbot
python -m pytest tests/test_agent_registry.py -v
```

Expected: `ModuleNotFoundError: No module named 'ai_server.agents.registry'`

- [ ] **Step 3: `registry.py` 구현**

`ai_server/agents/registry.py`:
```python
# ai_server/agents/registry.py
"""
에이전트 식별자 단일 진실 공급원 (Single Source of Truth).

에이전트를 추가하거나 rename할 때 이 파일만 수정하면 된다.
"""
from enum import StrEnum


class AgentKey(StrEnum):
    """에이전트 식별자 Enum. 값은 API·DB·프론트엔드 계약 문자열과 일치."""
    PROCESS_HISTORY = "process_history"
    RETURN_HISTORY  = "return_history"
    TEST_HISTORY    = "test_history"
    LONG_TERM       = "long_term"


# LangGraph 노드 이름 매핑 — graph.py가 이를 참조한다.
AGENT_NODE_MAP: dict[AgentKey, str] = {
    AgentKey.PROCESS_HISTORY: "process_history_node",
    AgentKey.RETURN_HISTORY:  "return_history_node",
    AgentKey.TEST_HISTORY:    "test_history_node",
    AgentKey.LONG_TERM:       "long_term_node",
}
```

- [ ] **Step 4: 테스트 실행 — PASS 확인**

```bash
python -m pytest tests/test_agent_registry.py -v
```

Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
cd 3_playground/display_defect_chatbot
git add ai_server/agents/registry.py tests/test_agent_registry.py
git commit -m "feat: add AgentKey StrEnum registry as single source of truth"
```

---

## Chunk 2: state.py에 AgentKey 적용

### Task 2: `HypothesisItem.recommended_agents` 타입 교체

**Files:**
- Modify: `3_playground/display_defect_chatbot/ai_server/agents/state.py`
- Test: `3_playground/display_defect_chatbot/tests/test_hypothesis_models.py` (기존 테스트 그대로 통과해야 함)

**현재 코드 (`state.py:23`):**
```python
recommended_agents: list[Literal["process_history", "return_history", "test_history", "long_term"]] = Field(
    description="추천 에이전트 목록"
)
```

**현재 코드 (`state.py:57`):**
```python
enabled_agents: list[str]
```

- [ ] **Step 1: 기존 테스트 PASS 확인 (baseline)**

```bash
python -m pytest tests/test_hypothesis_models.py tests/test_hypothesis_node.py -v
```

Expected: all passed (변경 전 baseline)

- [ ] **Step 2: `state.py` 수정**

`ai_server/agents/state.py` 상단 import 교체:
```python
# 제거
from typing import Annotated, Literal, Optional, TypedDict

# 추가
from typing import Annotated, Optional, TypedDict

from ai_server.agents.registry import AgentKey
```

`HypothesisItem.recommended_agents` 필드 교체:
```python
# 변경 전
recommended_agents: list[Literal["process_history", "return_history", "test_history", "long_term"]] = Field(
    description="추천 에이전트 목록"
)

# 변경 후
recommended_agents: list[AgentKey] = Field(
    description="추천 에이전트 목록"
)
```

`DefectAnalysisState.enabled_agents` 필드 교체:
```python
# 변경 전
enabled_agents: list[str]

# 변경 후
enabled_agents: list[AgentKey]
```

- [ ] **Step 3: 기존 테스트 PASS 확인**

```bash
python -m pytest tests/test_hypothesis_models.py tests/test_hypothesis_node.py tests/test_agent_registry.py -v
```

Expected: all passed

> **왜 테스트가 그대로 통과하는가?**
> - `StrEnum`은 `str`의 서브클래스이므로 `"process_history" == AgentKey.PROCESS_HISTORY`가 성립한다.
> - Pydantic v2는 문자열 입력을 `AgentKey`로 coerce한다.
> - `model_dump()` 직렬화: Pydantic v2는 `StrEnum`을 plain `str`로 직렬화하므로
>   `item.model_dump()["recommended_agents"] == ["process_history", ...]` 비교가 그대로 통과한다.
>   만약 테스트가 실패한다면 `model_dump(mode="json")`을 사용하거나 Pydantic 버전을 확인한다.

- [ ] **Step 4: 커밋**

```bash
cd 3_playground/display_defect_chatbot
git add ai_server/agents/state.py
git commit -m "refactor: use AgentKey enum in state.py (HypothesisItem, DefectAnalysisState)"
```

---

## Chunk 3: graph.py에 AgentKey 적용

### Task 3: `_NODE_MAP`과 `ALL_AGENTS`를 registry에서 파생

**Files:**
- Modify: `3_playground/display_defect_chatbot/ai_server/agents/graph.py`

**현재 코드 (`graph.py:39-45`):**
```python
_NODE_MAP = {
    "process_history": "process_history_node",
    "return_history":  "return_history_node",
    "test_history":    "test_history_node",
    "long_term":       "long_term_node",
}
ALL_AGENTS: list[str] = list(_NODE_MAP.keys())
```

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_agent_registry.py`에 추가:
```python
def test_graph_uses_agent_key_registry():
    """graph._NODE_MAP이 AgentKey를 키로 사용하고, ALL_AGENTS가 AgentKey 리스트인지 검증"""
    from ai_server.agents import graph
    from ai_server.agents.registry import AgentKey

    # _NODE_MAP의 모든 키가 AgentKey 인스턴스인지 확인
    for key in graph._NODE_MAP:
        assert isinstance(key, AgentKey), f"_NODE_MAP key {key!r} is not AgentKey"

    # ALL_AGENTS의 모든 원소가 AgentKey 인스턴스인지 확인
    for agent in graph.ALL_AGENTS:
        assert isinstance(agent, AgentKey), f"ALL_AGENTS entry {agent!r} is not AgentKey"
```

- [ ] **Step 2: 테스트 실행 — FAIL 확인**

```bash
cd 3_playground/display_defect_chatbot
python -m pytest tests/test_agent_registry.py::test_graph_uses_agent_key_registry -v
```

Expected: FAIL (`AssertionError: _NODE_MAP key 'process_history' is not AgentKey`)

- [ ] **Step 3: `graph.py` import에 registry 추가**

기존 import 블록에 한 줄 추가:
```python
from ai_server.agents.registry import AgentKey, AGENT_NODE_MAP
```

- [ ] **Step 4: `_NODE_MAP`, `ALL_AGENTS` 교체**

```python
# 변경 전
_NODE_MAP = {
    "process_history": "process_history_node",
    "return_history":  "return_history_node",
    "test_history":    "test_history_node",
    "long_term":       "long_term_node",
}
ALL_AGENTS: list[str] = list(_NODE_MAP.keys())

# 변경 후
_NODE_MAP: dict[AgentKey, str] = AGENT_NODE_MAP
ALL_AGENTS: list[AgentKey] = list(AgentKey)
```

- [ ] **Step 5: 전체 테스트 실행 — PASS 확인**

```bash
cd 3_playground/display_defect_chatbot
python -m pytest tests/ -v
```

Expected: all passed

> **동작 원리:** `StrEnum` 값은 `str`이므로 `Send(_NODE_MAP[key], sub_state)`에서 key 비교가 기존과 동일하게 동작한다. `route_to_agents`의 `key in _NODE_MAP` 체크도 `"process_history" in _NODE_MAP`이 `AgentKey.PROCESS_HISTORY`와 동등하게 처리된다.

- [ ] **Step 6: 커밋**

```bash
cd 3_playground/display_defect_chatbot
git add ai_server/agents/graph.py tests/test_agent_registry.py
git commit -m "refactor: graph.py derives _NODE_MAP and ALL_AGENTS from AgentKey registry"
```

---

## 완료 후 검증

에이전트를 새로 추가할 때의 변경 범위가 최소화됐는지 확인한다.

**예시: `visual_check` 에이전트 추가 시 수정할 파일:**

| 파일 | 변경 내용 |
|------|---------|
| `agents/registry.py` | `VISUAL_CHECK = "visual_check"` + `AGENT_NODE_MAP` 항목 1줄 |
| `agents/sub/visual_check.py` | 노드 함수 신규 작성 |
| `agents/state.py` | `visual_check_result` 필드 추가 (Generic State 도입 전까지) |
| `agents/prompts.py` | 프롬프트 설명 1줄 추가 |
| `frontend/useDefectChat.js` | `AGENT_CONFIG` 항목 1개 추가 |

**더 이상 필요 없는 작업:**
- ~~`graph.py`의 `_NODE_MAP`에 raw string 추가~~ → registry가 자동 반영
- ~~`state.py`의 `Literal[...]`에 값 추가~~ → `AgentKey` enum이 자동 반영
- ~~`server.py`의 `ALL_AGENTS` 수동 수정~~ → `list(AgentKey)`가 자동 반영

---

## 참고: 다음 단계 (이번 plan 범위 외)

이번 refactoring 후에도 state 필드(`process_history_result`, `return_history_result`, ...)가 에이전트별로 하나씩 남아있다. 에이전트를 추가할 때마다 state 필드도 수동으로 추가해야 한다.

이 문제는 **Generic State 패턴** (패턴 3)으로 해결할 수 있다:

```python
# 현재
process_history_result: Annotated[Optional[AgentAnalysisResult], lambda _, u: u]
return_history_result:  Annotated[Optional[AgentAnalysisResult], lambda _, u: u]
test_history_result:    Annotated[Optional[AgentAnalysisResult], lambda _, u: u]

# Generic State 도입 후
agent_results: Annotated[
    dict[AgentKey, AgentAnalysisResult],
    lambda old, new: {**old, **new}
]
```

이는 별도 plan으로 진행한다.
