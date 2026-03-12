# 가설별 에이전트 자동 추천 설계

**날짜:** 2026-03-11
**상태:** 승인됨

## 개요

LLM이 가설을 생성할 때 각 가설 검증에 필요한 에이전트를 함께 추천하고,
사용자가 가설을 선택하면 추천 에이전트가 기본값으로 활성화되도록 한다.
사용자는 이를 수동으로 변경할 수 있다.

## 변경 범위

### 1. `ai_server/agents/state.py`

Structured output용 Pydantic 모델 추가:

```python
class HypothesisItem(BaseModel):
    text: str = Field(description="가설 텍스트")
    recommended_agents: list[str] = Field(
        description="추천 에이전트 목록. 유효값: process_history, return_history, test_history, long_term"
    )

class HypothesesResponse(BaseModel):
    hypotheses: list[HypothesisItem]
```

`DefectAnalysisState` 타입 변경:

```python
# Before
hypotheses: list[str]

# After
hypotheses: list[dict]  # [{"text": str, "recommended_agents": list[str]}]
```

JSON 직렬화 호환성(AsyncPostgresSaver checkpointer)을 위해 state에는 `dict`로 저장.

### 2. `ai_server/agents/prompts.py`

`HYPOTHESIS_SYSTEM_PROMPT` 변경:
- 기존 텍스트 형식 지시 제거 (structured output이 형식 강제)
- 사용 가능한 에이전트 4종과 역할 설명 추가
- 각 가설마다 적합한 에이전트 추천 지시

```python
HYPOTHESIS_SYSTEM_PROMPT = """당신은 삼성 디스플레이 제조 공정 전문가입니다.
사용자가 보고한 픽셀 불량 증상과 과거 사례 문서를 바탕으로
원인 가설을 정확히 2-3개 제시하고, 각 가설 검증에 필요한 에이전트를 추천하세요.

사용 가능한 에이전트:
- process_history: 제조 공정 단계별 측정 이력 분석
- return_history: 반품/반송 이력 및 패턴 분석
- test_history: 전기·광학 테스트 결과 및 규격 초과 여부 분석
- long_term: 6개월 장기 불량 트렌드 분석 (시간이 오래 걸림)

각 가설마다 해당 가설 검증에 가장 적합한 에이전트를 1개 이상 추천하세요."""
```

### 3. `ai_server/agents/graph.py`

`hypothesis_node` 내 변경:

- `_llm.with_structured_output(HypothesesResponse)` 사용
- 기존 텍스트 파싱 루프 제거 (lines 64-70)
- interrupt 페이로드: `list[str]` → `list[dict]`
- state 업데이트: `hypotheses_data = [h.model_dump() for h in response.hypotheses]`

```python
# Before
response = await _llm.ainvoke(messages)
hypotheses = []
for line in text.split("\n"):
    if line.startswith("가설") and ":" in line:
        hypotheses.append(line)
resume = interrupt({"hypotheses": hypotheses})  # list[str]

# After
_hypothesis_llm = _llm.with_structured_output(HypothesesResponse)
response: HypothesesResponse = await _hypothesis_llm.ainvoke(messages)
hypotheses_data = [h.model_dump() for h in response.hypotheses]
resume = interrupt({"hypotheses": hypotheses_data})  # list[dict]
```

### 4. `frontend/src/components/HypothesisSelector.vue`

가설 텍스트 렌더링 변경:

```vue
<!-- Before -->
<span class="hyp-text">{{ h }}</span>
@click="$emit('select', h)"

<!-- After -->
<span class="hyp-text">{{ h.text }}</span>
@click="$emit('select', h)"   <!-- 객체 전체 전달 -->
```

### 5. `frontend/src/composables/useDefectChat.js`

`selectHypothesis` 함수에 추천 에이전트 pre-fill 로직 추가:

```javascript
// Before
function selectHypothesis(h) {
  selectedHypothesis.value = h
  step.value = 'agent_select'
}

// After
function selectHypothesis(h) {
  selectedHypothesis.value = h.text

  // 전체 초기화 후 추천 에이전트만 ON
  AGENT_CONFIG.forEach(a => { enabledAgents[a.key] = false })
  h.recommended_agents.forEach(key => { enabledAgents[key] = true })

  step.value = 'agent_select'
}
```

## 데이터 흐름

```
hypothesis_node
  → with_structured_output(HypothesesResponse)
  → interrupt({"hypotheses": [{"text": "...", "recommended_agents": [...]}, ...]})

프론트엔드
  → HypothesisSelector: h.text 렌더링
  → 사용자 가설 선택 → selectHypothesis(h)
    → selectedHypothesis = h.text
    → enabledAgents 초기화 → h.recommended_agents 활성화
  → AgentSelector: 추천 에이전트 ON 상태로 표시 (수동 변경 가능)
  → runAgents() → resume {selected_hypothesis, enabled_agents} 전송 (변경 없음)
```

## 변경되지 않는 것

- `AgentSelector.vue`: enabledAgents 객체 그대로 사용
- `runAgents()`: resume 페이로드 형식 동일
- `route_to_agents()`: enabled_agents 처리 로직 동일
- 하위 에이전트(process_history, return_history, test_history, long_term): 변경 없음
- checkpointer, RAG, synthesis_node: 변경 없음

## 파일 변경 요약

| 파일 | 변경 유형 |
|------|----------|
| `ai_server/agents/state.py` | 모델 추가, 타입 변경 |
| `ai_server/agents/prompts.py` | 프롬프트 수정 |
| `ai_server/agents/graph.py` | structured output 적용, 파싱 제거 |
| `frontend/src/components/HypothesisSelector.vue` | 렌더링 수정 |
| `frontend/src/composables/useDefectChat.js` | pre-fill 로직 추가 |
