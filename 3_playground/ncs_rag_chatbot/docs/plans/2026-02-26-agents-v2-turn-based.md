# Agents v2 Turn-Based Handoffs Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** v2 에이전트를 "사용자 요청 1회 = 1단계 진행"으로 전환한다 — `handoff_to_*` 자동전환 도구를 제거하고 `complete_*_step` 도구로 교체, 각 단계 프롬프트가 사용자에게 먼저 질문하도록 변경.

**Architecture:** 단일 `create_agent` 인스턴스 + middleware(step_config) 구조는 유지. `handoff_to_rag`/`handoff_to_feedback` 제거, `complete_sql_step`/`complete_rag_step` 추가. 각 단계 프롬프트는 "tool 호출 → 결과 보고 → complete_*_step 호출 → 다음 단계 프롬프트가 사용자에게 질문" 순서로 동작해 invoke가 자연 종료된다.

**Tech Stack:** langchain (create_agent, wrap_model_call, ToolRuntime), langgraph (InMemorySaver, Command), pytest-asyncio

---

## Task 1: 테스트 업데이트 — 새 도구 이름으로 교체

**Files:**
- Modify: `ai_server/tests/test_agents.py`

**Step 1: 변경 대상 테스트 확인**

현재 아래 두 테스트가 `handoff_to_rag`, `handoff_to_feedback`을 기대한다:
- `test_ncs_handoff_agent_has_three_step_workflow` (line 110~134)
- `test_ncs_handoff_agent_handoff_tools_are_registered` (line 163~170)

**Step 2: 테스트 교체**

`test_ncs_handoff_agent_has_three_step_workflow` 전체를 아래로 교체:

```python
async def test_ncs_handoff_agent_has_three_step_workflow():
    """NCSHandoffAgent는 sql, rag, feedback 세 단계 워크플로우를 지원한다."""
    from agents.v2.supervisor import NCSHandoffAgent

    mock_sql_tool = MagicMock()
    mock_sql_tool.name = "query_employee_data"
    mock_rag_tool = MagicMock()
    mock_rag_tool.name = "retrieve_context"

    with patch("langchain.agents.create_agent") as mock_create, \
         patch("langchain.chat_models.init_chat_model"):
        mock_create.return_value = MagicMock()
        agent = NCSHandoffAgent(
            rag_tools=[mock_rag_tool],
            sql_tools=[mock_sql_tool],
        )
        agent.create_agent()

    call_kwargs = mock_create.call_args[1]
    tool_names = [t.name for t in call_kwargs["tools"]]
    assert "complete_sql_step" in tool_names
    assert "complete_rag_step" in tool_names
    assert "query_employee_data" in tool_names
    assert "retrieve_context" in tool_names
```

`test_ncs_handoff_agent_handoff_tools_are_registered` 전체를 아래로 교체:

```python
async def test_ncs_handoff_agent_transition_tools_are_registered():
    """complete_sql_step, complete_rag_step는 @tool로 등록된 LangChain 도구다."""
    from agents.v2.supervisor import complete_sql_step, complete_rag_step

    assert hasattr(complete_sql_step, "name")
    assert complete_sql_step.name == "complete_sql_step"
    assert hasattr(complete_rag_step, "name")
    assert complete_rag_step.name == "complete_rag_step"
```

**Step 3: 테스트 실행 — 실패 확인**

```bash
cd ai_server
python -m pytest tests/test_agents.py::test_ncs_handoff_agent_has_three_step_workflow \
                 tests/test_agents.py::test_ncs_handoff_agent_transition_tools_are_registered \
                 -v
# 출력: FAILED (ImportError: cannot import name 'complete_sql_step')
```

**Step 4: Commit**

```bash
git add ai_server/tests/test_agents.py
git commit -m "test(agents/v2): handoff → complete_*_step 도구 이름으로 테스트 교체"
```

---

## Task 2: supervisor.py — 도구 및 프롬프트 교체

**Files:**
- Modify: `ai_server/agents/v2/supervisor.py`

**Step 1: 현재 파일 구조 파악**

변경 대상:
1. `handoff_to_rag` 함수 → `complete_sql_step`으로 교체
2. `handoff_to_feedback` 함수 → `complete_rag_step`으로 교체
3. `SQL_STEP_PROMPT` — "사용자에게 질문 먼저" 방식으로 변경
4. `RAG_STEP_PROMPT` — "NCS 항목 먼저 물어봐" 방식으로 변경
5. `FEEDBACK_STEP_PROMPT` — "피드백 관점 먼저 물어봐" 방식으로 변경
6. `create_agent()` 내부 `step_config` 도구 목록 업데이트

**Step 2: 도구 교체**

`handoff_to_rag` 함수 전체를 아래로 교체:

```python
@tool
def complete_sql_step(runtime: ToolRuntime[None, NCSAgentState]) -> Command:
    """직원 이력 조회 완료 후 NCS 문서 검색 단계로 전환한다."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content="직원 이력 수집 완료. NCS 문서 검색 단계로 전환합니다.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "current_step": "rag",
        }
    )
```

`handoff_to_feedback` 함수 전체를 아래로 교체:

```python
@tool
def complete_rag_step(runtime: ToolRuntime[None, NCSAgentState]) -> Command:
    """NCS 문서 검색 완료 후 종합 피드백 생성 단계로 전환한다."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content="NCS 문서 검색 완료. 종합 피드백 생성 단계로 전환합니다.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "current_step": "feedback",
        }
    )
```

**Step 3: 프롬프트 교체**

`SQL_STEP_PROMPT` 전체를 아래로 교체:

```python
SQL_STEP_PROMPT = (
    "너는 NCS 직원 이력 조회 전문가야.\n"
    "사용자 메시지에서 사번(예: EMP001) 또는 직원 이름을 파악하여 "
    "query_employee_data 도구로 이력을 조회해.\n"
    "조회가 완료되면:\n"
    "1. 결과를 사용자에게 간략히 요약해서 보여줘\n"
    "2. complete_sql_step 도구를 호출해서 다음 단계로 전환해\n"
    "절대로 직접 NCS 문서 검색을 수행하지 마."
)
```

`RAG_STEP_PROMPT` 전체를 아래로 교체:

```python
RAG_STEP_PROMPT = (
    "너는 NCS 문서 검색 전문가야.\n"
    "직전 대화에서 직원 이력이 조회되었다.\n"
    "먼저 사용자에게 어떤 NCS 항목 또는 키워드를 기준으로 검색할지 물어봐.\n"
    "사용자가 답변하면:\n"
    "1. retrieve_context 도구로 관련 NCS 기준 문서를 검색해\n"
    "2. 검색 결과를 사용자에게 요약해서 보여줘\n"
    "3. complete_rag_step 도구를 호출해서 다음 단계로 전환해\n"
    "절대로 직접 피드백을 생성하지 마."
)
```

`FEEDBACK_STEP_PROMPT` 전체를 아래로 교체:

```python
FEEDBACK_STEP_PROMPT = (
    "너는 NCS 직원 관리 피드백 전문가야.\n"
    "이전 대화에서 수집된 직원 이력 데이터와 NCS 문서 검색 결과를 확인했다.\n"
    "먼저 사용자에게 어떤 관점으로 피드백을 작성할지 물어봐 "
    "(예: 강점 중심 / 개선점 중심 / 균형 있게).\n"
    "사용자가 방향을 제시하면 마크다운 형식으로 종합 피드백을 작성해줘.\n"
    "직원 이력과 NCS 기준을 항목별로 비교하고 구체적인 개선 방향을 제시해줘.\n"
    "불확실한 내용은 반드시 명시해."
)
```

**Step 4: create_agent() 내부 step_config 업데이트**

`create_agent()` 내부의 `step_config` 딕셔너리를 아래로 교체:

```python
        step_config = {
            "sql": {
                "prompt": SQL_STEP_PROMPT,
                "tools": self._sql_tools + [complete_sql_step],
            },
            "rag": {
                "prompt": RAG_STEP_PROMPT,
                "tools": self._rag_tools + [complete_rag_step],
            },
            "feedback": {
                "prompt": FEEDBACK_STEP_PROMPT,
                "tools": [],
            },
        }
```

`all_tools` 라인도 업데이트:

```python
        all_tools = self._sql_tools + self._rag_tools + [complete_sql_step, complete_rag_step]
```

**Step 5: 테스트 실행 — 통과 확인**

```bash
cd ai_server
python -m pytest tests/test_agents.py -v
# 출력: 16 passed
```

**Step 6: Commit**

```bash
git add ai_server/agents/v2/supervisor.py
git commit -m "feat(agents/v2): handoff → complete_*_step 교체, 단계별 질문 수집 프롬프트"
```

---

## 최종 파일 목록

| 파일 | 변경 |
|------|------|
| `ai_server/agents/v2/supervisor.py` | 도구 2개 교체, 프롬프트 3개 수정, step_config/all_tools 업데이트 |
| `ai_server/tests/test_agents.py` | 테스트 2개 업데이트 |
