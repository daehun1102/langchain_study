# Hypothesis Agent Recommendation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** LLM이 가설 생성 시 각 가설별 추천 에이전트를 함께 반환하고, 사용자가 가설을 선택하면 추천 에이전트가 기본 활성화된다.

**Architecture:** `hypothesis_node`에서 `with_structured_output(HypothesesResponse)`로 가설+추천 에이전트를 타입-안전하게 추출. interrupt 페이로드를 `list[dict]`로 변경. 프론트엔드는 가설 선택 시 `recommended_agents`로 `enabledAgents`를 pre-fill (가설 선택 이후 사용자 수동 변경 가능).

**Tech Stack:** Python 3.11, Pydantic v2, LangChain `with_structured_output`, LangGraph interrupt/resume, Vue 3 Composition API, pytest

---

## File Map

| 파일 | 변경 유형 | 역할 |
|------|----------|------|
| `ai_server/agents/state.py` | Modify | `HypothesisItem`, `HypothesesResponse` 모델 추가. `hypotheses: list[dict]` 타입 변경 |
| `ai_server/agents/prompts.py` | Modify | `HYPOTHESIS_SYSTEM_PROMPT` 에이전트 설명 추가, 형식 지시 제거 |
| `ai_server/agents/graph.py` | Modify | `hypothesis_node` structured output 적용, 텍스트 파싱 제거, `_hypothesis_llm` 모듈 레벨 추가 |
| `frontend/src/components/HypothesisSelector.vue` | Modify | `{{ h }}` → `{{ h.text }}` |
| `frontend/src/composables/useDefectChat.js` | Modify | `selectHypothesis` pre-fill 로직 추가 (line 199) |
| `conftest.py` | Create | pytest PYTHONPATH 설정 |
| `tests/__init__.py` | Create | 테스트 패키지 초기화 |
| `tests/test_hypothesis_models.py` | Create | Pydantic 모델 단위 테스트 |
| `tests/test_hypothesis_node.py` | Create | `hypothesis_node` 변환 로직 테스트 |

모든 경로는 `display_defect_chatbot/` 기준 상대경로. pytest는 항상 `display_defect_chatbot/` 루트에서 실행.

---

## Chunk 1: 테스트 환경 + Backend 모델

### Task 0: pytest 환경 설정

**Files:**
- Create: `conftest.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: conftest.py 생성**

`display_defect_chatbot/conftest.py` 생성:

```python
# conftest.py
import sys
import os

# ai_server 패키지를 import 가능하게 경로 추가
# __file__은 display_defect_chatbot/conftest.py이므로 dirname이 곧 패키지 루트
sys.path.insert(0, os.path.dirname(__file__))
```

- [ ] **Step 2: tests 디렉토리 및 __init__.py 생성**

```bash
mkdir -p tests && touch tests/__init__.py
```

- [ ] **Step 3: pytest 설치 확인**

```bash
python -m pytest --version
```

Expected: `pytest 7.x.x` 또는 이상. 없으면 `pip install pytest`

---

### Task 1: Pydantic 모델 추가 및 state 타입 변경

**Files:**
- Modify: `ai_server/agents/state.py`
- Create: `tests/test_hypothesis_models.py`

- [ ] **Step 1: 테스트 파일 생성**

`tests/test_hypothesis_models.py` 생성:

```python
# tests/test_hypothesis_models.py
import pytest
from pydantic import ValidationError
from ai_server.agents.state import HypothesisItem, HypothesesResponse


def test_hypothesis_item_valid():
    item = HypothesisItem(
        text="가설1: 공정 오염 — 증착 공정 중 파티클 유입",
        recommended_agents=["process_history", "test_result"],
    )
    assert item.text == "가설1: 공정 오염 — 증착 공정 중 파티클 유입"
    assert item.recommended_agents == ["process_history", "test_result"]


def test_hypothesis_item_model_dump():
    item = HypothesisItem(
        text="가설2: 전극 단선",
        recommended_agents=["return_history"],
    )
    d = item.model_dump()
    assert d == {"text": "가설2: 전극 단선", "recommended_agents": ["return_history"]}


def test_hypotheses_response_valid():
    resp = HypothesesResponse(
        hypotheses=[
            HypothesisItem(text="가설1", recommended_agents=["process_history"]),
            HypothesisItem(text="가설2", recommended_agents=["return_history", "long_term"]),
        ]
    )
    assert len(resp.hypotheses) == 2
    assert resp.hypotheses[0].text == "가설1"


def test_hypotheses_response_missing_field_raises():
    with pytest.raises(ValidationError):
        HypothesesResponse()
```

- [ ] **Step 2: 테스트 실행 — FAIL 확인**

```bash
python -m pytest tests/test_hypothesis_models.py -v
```

Expected: `ImportError: cannot import name 'HypothesisItem' from 'ai_server.agents.state'`

- [ ] **Step 3: `state.py`에 모델 추가**

[ai_server/agents/state.py](ai_server/agents/state.py)의 `AgentOutputSchema` 클래스 바로 아래에 추가:

```python
class HypothesisItem(BaseModel):
    """가설 하나와 추천 에이전트 목록"""
    text: str = Field(description="가설 텍스트")
    recommended_agents: list[str] = Field(
        description="추천 에이전트 목록. 유효값: process_history, return_history, test_result, long_term"
    )


class HypothesesResponse(BaseModel):
    """hypothesis_node structured output 스키마"""
    hypotheses: list[HypothesisItem]
```

그리고 `DefectAnalysisState`의 `hypotheses` 타입 변경:

```python
# Before (line 48)
hypotheses: list[str]

# After
hypotheses: list[dict]  # [{"text": str, "recommended_agents": list[str]}]
```

- [ ] **Step 4: 테스트 실행 — PASS 확인**

```bash
python -m pytest tests/test_hypothesis_models.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add conftest.py tests/ ai_server/agents/state.py
git commit -m "feat(state): add HypothesisItem and HypothesesResponse pydantic models"
```

---

### Task 2: HYPOTHESIS_SYSTEM_PROMPT 수정

**Files:**
- Modify: `ai_server/agents/prompts.py`

- [ ] **Step 1: `HYPOTHESIS_SYSTEM_PROMPT` 교체**

[ai_server/agents/prompts.py](ai_server/agents/prompts.py)에서 `HYPOTHESIS_SYSTEM_PROMPT` 전체를 교체:

```python
HYPOTHESIS_SYSTEM_PROMPT = """당신은 삼성 디스플레이 제조 공정 전문가입니다.
사용자가 보고한 픽셀 불량 증상과 과거 사례 문서를 바탕으로
원인 가설을 정확히 2-3개 제시하고, 각 가설 검증에 필요한 에이전트를 추천하세요.

사용 가능한 에이전트:
- process_history: 제조 공정 단계별 측정 이력 분석
- return_history: 반품/반송 이력 및 패턴 분석
- test_result: 전기·광학 테스트 결과 및 규격 초과 여부 분석
- long_term: 6개월 장기 불량 트렌드 분석 (시간이 오래 걸림)

각 가설마다 해당 가설 검증에 가장 적합한 에이전트를 1개 이상 추천하세요."""
```

- [ ] **Step 2: 변경 검증**

```bash
python -c "from ai_server.agents.prompts import HYPOTHESIS_SYSTEM_PROMPT; assert 'process_history' in HYPOTHESIS_SYSTEM_PROMPT; assert '응답 형식' not in HYPOTHESIS_SYSTEM_PROMPT; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add ai_server/agents/prompts.py
git commit -m "feat(prompts): add agent descriptions to HYPOTHESIS_SYSTEM_PROMPT"
```

---

## Chunk 2: hypothesis_node structured output 적용

### Task 3: graph.py — hypothesis_node 교체

**Files:**
- Modify: `ai_server/agents/graph.py`
- Create: `tests/test_hypothesis_node.py`

- [ ] **Step 1: 테스트 파일 생성**

`tests/test_hypothesis_node.py` 생성:

```python
# tests/test_hypothesis_node.py
"""
hypothesis_node의 structured output 변환 로직 단위 테스트.
Task 3 Step 3 이후 graph.py import 검증 포함 (red-green TDD).
"""
import pytest
from ai_server.agents.state import HypothesisItem, HypothesesResponse


def make_mock_response():
    return HypothesesResponse(
        hypotheses=[
            HypothesisItem(
                text="가설1: 공정 오염 — 증착 챔버 파티클",
                recommended_agents=["process_history", "test_result"],
            ),
            HypothesisItem(
                text="가설2: 전극 단선 — 식각 과도",
                recommended_agents=["return_history", "process_history"],
            ),
        ]
    )


def test_model_dump_produces_correct_list():
    """model_dump()로 state 저장 형식(list[dict]) 변환 검증"""
    resp = make_mock_response()
    hypotheses_data = [h.model_dump() for h in resp.hypotheses]

    assert len(hypotheses_data) == 2
    assert hypotheses_data[0]["text"] == "가설1: 공정 오염 — 증착 챔버 파티클"
    assert hypotheses_data[0]["recommended_agents"] == ["process_history", "test_result"]


def test_interrupt_payload_has_required_keys():
    """interrupt 페이로드가 text와 recommended_agents 키를 포함하는지 검증"""
    resp = make_mock_response()
    hypotheses_data = [h.model_dump() for h in resp.hypotheses]
    payload = {"hypotheses": hypotheses_data}

    assert isinstance(payload["hypotheses"], list)
    assert "text" in payload["hypotheses"][0]
    assert "recommended_agents" in payload["hypotheses"][0]


def test_resume_dict_extracts_correctly():
    """resume dict에서 selected_hypothesis, enabled_agents 추출 검증"""
    resume = {
        "selected_hypothesis": "가설1: 공정 오염",
        "enabled_agents": ["process_history", "test_result"],
    }
    assert resume.get("selected_hypothesis") == "가설1: 공정 오염"
    assert resume.get("enabled_agents") == ["process_history", "test_result"]


def test_hypothesis_llm_exists_in_graph():
    """graph.py에 _hypothesis_llm 모듈 레벨 변수가 존재하는지 검증 (Step 3 이후 green)"""
    from ai_server.agents import graph
    assert hasattr(graph, "_hypothesis_llm"), "_hypothesis_llm must be defined at module level"
```

- [ ] **Step 2: 테스트 실행 — 마지막 테스트만 FAIL 확인**

```bash
python -m pytest tests/test_hypothesis_node.py -v
```

Expected: 처음 3개 PASS, `test_hypothesis_llm_exists_in_graph` FAIL (`AssertionError: _hypothesis_llm must be defined at module level`)

- [ ] **Step 3: `graph.py` — import 추가 + `_hypothesis_llm` 모듈 레벨 추가**

[ai_server/agents/graph.py](ai_server/agents/graph.py)의 import 수정 (line 23):

```python
# Before
from ai_server.agents.state import DefectAnalysisState, SubAgentInput

# After
from ai_server.agents.state import DefectAnalysisState, SubAgentInput, HypothesesResponse
```

그리고 line 34(`_chat_llm = ...`) 바로 다음 줄에 추가:

```python
_hypothesis_llm = _llm.with_structured_output(HypothesesResponse)
```

- [ ] **Step 4: 테스트 실행 — 4개 모두 PASS 확인**

```bash
python -m pytest tests/test_hypothesis_node.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: `hypothesis_node` 함수 교체**

[ai_server/agents/graph.py:49-88](ai_server/agents/graph.py#L49-L88)의 `hypothesis_node` 함수 전체를 교체:

```python
async def hypothesis_node(state: DefectAnalysisState, config: RunnableConfig) -> dict:
    """RAG 검색 → structured output으로 가설+추천 에이전트 생성 → interrupt → 선택된 가설 수신"""
    vsm: VectorStoreManager = config["configurable"]["vsm"]
    docs = await vsm.similarity_search(state["defect_description"], k=4)
    context = "\n\n".join([d.page_content for d in docs]) if docs else "관련 사례 없음"

    messages = [
        SystemMessage(content=HYPOTHESIS_SYSTEM_PROMPT),
        HumanMessage(
            content=f"[보고 회사]: {state['company']}\n[불량 증상]: {state['defect_description']}\n\n[과거 사례 문서]\n{context}"
        ),
    ]
    response: HypothesesResponse = await _hypothesis_llm.ainvoke(messages)
    hypotheses_data = [h.model_dump() for h in response.hypotheses]

    # interrupt: 클라이언트에 가설 목록(text + recommended_agents) 반환
    # resume 값은 {"selected_hypothesis": str, "enabled_agents": list} 형태의 dict
    resume = interrupt({"hypotheses": hypotheses_data})

    if isinstance(resume, dict):
        selected = resume.get("selected_hypothesis", "")
        enabled = resume.get("enabled_agents")
    else:
        selected = str(resume)
        enabled = None

    result: dict = {"hypotheses": hypotheses_data, "selected_hypothesis": selected}
    if enabled is not None:
        result["enabled_agents"] = enabled
    if isinstance(resume, dict) and resume.get("notify_email") is not None:
        result["notify_email"] = resume["notify_email"]
    return result
```

- [ ] **Step 6: import 검증**

```bash
python -c "from ai_server.agents.graph import build_investigation_graph; print('OK')"
```

Expected: `OK`

- [ ] **Step 7: 전체 테스트 실행**

```bash
python -m pytest tests/ -v
```

Expected: 8 tests PASS

- [ ] **Step 8: Commit**

```bash
git add ai_server/agents/graph.py tests/test_hypothesis_node.py
git commit -m "feat(graph): apply structured output to hypothesis_node, remove text parsing"
```

---

## Chunk 3: 프론트엔드 — 가설 선택 + 에이전트 pre-fill

### Task 4: HypothesisSelector.vue — h.text 렌더링

**Files:**
- Modify: `frontend/src/components/HypothesisSelector.vue`

- [ ] **Step 1: 가설 텍스트 렌더링 변경**

[frontend/src/components/HypothesisSelector.vue](frontend/src/components/HypothesisSelector.vue)에서:

```vue
<!-- Before -->
<span class="hyp-text">{{ h }}</span>

<!-- After -->
<span class="hyp-text">{{ h.text }}</span>
```

`@click="$emit('select', h)"` 은 변경 없음 (객체 전체 전달).

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/HypothesisSelector.vue
git commit -m "feat(frontend): render h.text in HypothesisSelector for hypothesis object"
```

---

### Task 5: useDefectChat.js — selectHypothesis pre-fill 추가

**Files:**
- Modify: `frontend/src/composables/useDefectChat.js`

**동작 설명:**
- `selectHypothesis(h)` 호출 시 `enabledAgents` 전체를 `false`로 초기화한 뒤, `h.recommended_agents`에 있는 에이전트만 `true`로 설정
- 가설 선택 이후 사용자가 에이전트를 수동으로 켜고 끌 수 있으며, 이는 기존 `toggleAgent()` 함수가 그대로 처리
- 세션 저장 시 `selectedHypothesis.value`는 `h.text` (문자열)로 저장되므로 구버전 세션과 호환됨

- [ ] **Step 1: `selectHypothesis` 함수 수정 (line 199)**

[frontend/src/composables/useDefectChat.js:199-202](frontend/src/composables/useDefectChat.js#L199-L202):

```javascript
// Before
function selectHypothesis(hypothesis) {
  selectedHypothesis.value = hypothesis
  step.value = 'agent_select'
}

// After
function selectHypothesis(h) {
  selectedHypothesis.value = h.text

  // 가설 선택 시 전체 초기화 후 추천 에이전트만 ON (이후 수동 변경 가능)
  AGENT_CONFIG.forEach(a => { enabledAgents[a.key] = false })
  h.recommended_agents.forEach(key => { enabledAgents[key] = true })

  step.value = 'agent_select'
}
```

- [ ] **Step 2: 수동 동작 검증**

브라우저에서:
1. 불량 정보 입력 후 분석 시작
2. 가설 목록 화면 확인 — 가설 텍스트가 정상 렌더링되는지 확인
3. 가설 카드 클릭 → 에이전트 선택 화면에서 해당 가설의 `recommended_agents`만 ON인지 확인
4. 에이전트 수동 토글이 정상 동작하는지 확인
5. 분석 실행 후 선택된 에이전트만 실행되는지 확인

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useDefectChat.js
git commit -m "feat(frontend): pre-fill recommended agents on hypothesis selection"
```

---

## 완료 기준

- [ ] `python -m pytest tests/ -v` → 8 tests PASS
- [ ] 브라우저에서 가설 선택 시 추천 에이전트가 ON으로 pre-fill됨
- [ ] 사용자가 에이전트를 수동 변경 가능 (toggle 동작)
- [ ] 추천되지 않은 에이전트는 OFF 상태로 시작
