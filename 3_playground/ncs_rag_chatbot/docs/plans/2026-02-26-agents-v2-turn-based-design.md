# Agents v2 Turn-Based Handoffs Design

**Date:** 2026-02-26
**Scope:** `ai_server/agents/v2/supervisor.py`, `ai_server/tests/test_agents.py`

---

## 목표

기존 v2의 "1회 요청 → 3단계 자동 완주" 방식을 LangChain 문서의 state machine 패턴에 맞게
"사용자 요청 1회 = 1단계 진행"으로 전환한다.

---

## 흐름

```
Turn 1: 사용자 "EMP001 피드백해줘"
  [sql config] → query_employee_data 호출 → 결과 요약
               → complete_sql_step() → current_step = "rag"
               → [rag config] "어떤 NCS 항목 기준으로 검색할까요?"
  invoke 종료

Turn 2: 사용자 "직무능력, 훈련시간 기준으로"
  [rag config] → retrieve_context 호출 → 결과 요약
               → complete_rag_step() → current_step = "feedback"
               → [feedback config] "어떤 관점으로 피드백 작성할까요?"
  invoke 종료

Turn 3: 사용자 "개선점 중심으로"
  [feedback config] → 최종 피드백 생성 (툴 없음)
  invoke 종료
```

한 invoke 안에서 상태 전환 후 다음 단계 config가 즉시 적용되며, 다음 단계가
사용자에게 질문을 던지면서 자연스럽게 invoke가 종료된다 (interrupt 불필요).

---

## 상태 스키마

```python
class NCSAgentState(AgentState):
    current_step: NotRequired[Literal["sql", "rag", "feedback"]]
```

직원 이력, RAG 결과 등 실제 데이터는 메시지 히스토리에 저장된다.
checkpointer(InMemorySaver)가 thread_id별로 전체 메시지를 보존한다.

---

## 도구 변경

### 제거
- `handoff_to_rag`
- `handoff_to_feedback`

### 추가
```python
@tool
def complete_sql_step(runtime: ToolRuntime[None, NCSAgentState]) -> Command:
    """직원 이력 조회 완료 후 RAG 단계로 전환한다."""
    return Command(update={
        "messages": [ToolMessage(content="SQL 단계 완료.", tool_call_id=runtime.tool_call_id)],
        "current_step": "rag",
    })

@tool
def complete_rag_step(runtime: ToolRuntime[None, NCSAgentState]) -> Command:
    """NCS 문서 검색 완료 후 피드백 단계로 전환한다."""
    return Command(update={
        "messages": [ToolMessage(content="RAG 단계 완료.", tool_call_id=runtime.tool_call_id)],
        "current_step": "feedback",
    })
```

---

## 단계별 설정

```python
step_config = {
    "sql": {
        "prompt": SQL_PROMPT,
        "tools": [query_employee_data, complete_sql_step],
    },
    "rag": {
        "prompt": RAG_PROMPT,
        "tools": [retrieve_context, complete_rag_step],
    },
    "feedback": {
        "prompt": FEEDBACK_PROMPT,
        "tools": [],
    },
}
```

---

## 프롬프트 설계 원칙

- **SQL**: 직원 이력 조회 → 결과 요약 → `complete_sql_step` 호출. 직접 RAG 검색 금지.
- **RAG**: 사용자에게 검색 항목 확인 → `retrieve_context` 호출 → 결과 요약 → `complete_rag_step` 호출.
- **Feedback**: 메시지 히스토리의 이력+문서 데이터 기반 피드백 작성. 툴 없음.

---

## 참고 문서

- https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs-customer-support
