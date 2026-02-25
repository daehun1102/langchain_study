# Agents v2 — LangChain Handoffs 설계

**Date:** 2026-02-25
**Status:** Approved

## 목표

v1의 Supervisor + RAG + SQL 3-에이전트 구조를 LangChain handoffs 패턴으로 재구현한다.
단일 `create_agent` 인스턴스가 `current_step` 상태에 따라 system_prompt와 tools를 동적으로 교체하며 순차 워크플로우를 수행한다.

---

## Handoffs 패턴 핵심

```
v1: Supervisor(LLM) → RAG agent(LLM) + SQL agent(LLM)  [3개의 독립 에이전트]
v2: 단일 create_agent(model, state_schema, middleware)   [미들웨어가 행동 교체]
```

**동작 원리:**
1. 매 model call 직전에 미들웨어 실행
2. 미들웨어가 `current_step` 읽어 system_prompt + tools override
3. 핸드오프 도구가 `Command(update={"current_step": "next"})` 반환 → 다음 call은 새 설정

**사용자 입력 전달 방식:**
- v1: Supervisor가 사용자 입력을 가공해 서브에이전트에 전달
- v2: 사용자 입력이 conversation history를 통해 각 step에 직접 전달

---

## 3단계 순차 워크플로우

고객지원 튜토리얼(`warranty_collector → issue_classifier → resolution_specialist`) 패턴 적용:

| step | 역할 | tools | 전환 |
|------|------|-------|------|
| `"sql"` (default) | 직원 이력 조회 | `[query_employee_data, handoff_to_rag]` | → `"rag"` |
| `"rag"` | NCS 문서 검색 | `[retrieve_context, handoff_to_feedback]` | → `"feedback"` |
| `"feedback"` | 종합 피드백 생성 | `[]` | → END |

**흐름 예시:**
```
User: "EMP001의 NCS 과제 피드백해줘"
  → model call #1 (sql): query_employee_data("EMP001") → handoff_to_rag()
  → model call #2 (rag): retrieve_context("EMP001 NCS 과제") → handoff_to_feedback()
  → model call #3 (feedback): 직원 데이터 + NCS 문서 종합 → 최종 답변 반환
```

---

## 상태 스키마

```python
from langchain.agents import AgentState
from typing import Literal
from typing_extensions import NotRequired

NCSStep = Literal["sql", "rag", "feedback"]

class NCSAgentState(AgentState):
    current_step: NotRequired[NCSStep]   # 기본값: "sql"
```

---

## 핸드오프 도구

```python
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langgraph.types import Command

@tool
def handoff_to_rag(runtime: ToolRuntime[None, NCSAgentState]) -> Command:
    """직원 이력 수집 완료 후 NCS 문서 검색 단계로 전환한다."""
    return Command(update={
        "messages": [ToolMessage(content="RAG 검색 단계로 전환", tool_call_id=runtime.tool_call_id)],
        "current_step": "rag",
    })

@tool
def handoff_to_feedback(runtime: ToolRuntime[None, NCSAgentState]) -> Command:
    """NCS 문서 검색 완료 후 종합 피드백 생성 단계로 전환한다."""
    return Command(update={
        "messages": [ToolMessage(content="피드백 생성 단계로 전환", tool_call_id=runtime.tool_call_id)],
        "current_step": "feedback",
    })
```

---

## 미들웨어

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

STEP_CONFIG = {
    "sql": {
        "prompt": SQL_PROMPT,
        "tools": [query_employee_data, handoff_to_rag],
    },
    "rag": {
        "prompt": RAG_PROMPT,
        "tools": [retrieve_context, handoff_to_feedback],
    },
    "feedback": {
        "prompt": FEEDBACK_PROMPT,
        "tools": [],
    },
}

@wrap_model_call
def apply_ncs_step_config(request: ModelRequest, handler) -> ModelResponse:
    current_step = request.state.get("current_step", "sql")
    config = STEP_CONFIG[current_step]
    request = request.override(
        system_prompt=config["prompt"],
        tools=config["tools"],
    )
    return handler(request)
```

---

## NCSHandoffAgent 클래스

```python
class NCSHandoffAgent(BaseAgent):
    def __init__(self, rag_tools, sql_tools, model_name=None):
        all_tools = sql_tools + rag_tools + [handoff_to_rag, handoff_to_feedback]
        self.agent = create_agent(
            init_chat_model(model_name or settings.model_name),
            tools=all_tools,
            state_schema=NCSAgentState,
            middleware=[apply_ncs_step_config],
            checkpointer=InMemorySaver(),
        )

    def create_agent(self, tools=None): pass   # BaseAgent 요구사항 충족

    async def run(self, query: str, config: dict = None):
        last_message = None
        async for event in self.agent.astream(
            {"messages": [{"role": "user", "content": query}]},
            config=config or {},
            stream_mode="values",
        ):
            last_message = event["messages"][-1]
        return last_message
```

---

## 변경 파일 목록

### 신규
| 파일 | 내용 |
|------|------|
| `ai_server/agents/v2/__init__.py` | 빈 파일 |
| `ai_server/agents/v2/supervisor.py` | NCSHandoffAgent + 모든 구성 포함 |

### 수정
| 파일 | 변경 |
|------|------|
| `ai_server/agents/factory.py` | `version` 파라미터 → v2이면 NCSHandoffAgent 반환 |
| `ai_server/config.py` | `agent_version: str` 추가 (env: AGENT_VERSION, default: "v1") |
| `ai_server/server.py` | `create_agent(vsm, version=settings.agent_version)` |

### 무수정
- `ai_server/tools/rag_tool.py` — `retrieve_context` 그대로 사용
- `ai_server/tools/sql_tool.py` — `query_employee_data` 그대로 사용
- `ai_server/agents/v1/` — v1 코드 유지

---

## 참고 자료
- LangChain handoffs 문서: https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs.md
- 튜토리얼 노트북: `2_tutorials/multi_agent/handoff.ipynb`
