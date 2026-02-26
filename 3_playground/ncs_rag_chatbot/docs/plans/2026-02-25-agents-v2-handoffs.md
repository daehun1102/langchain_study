# Agents v2 Handoffs Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** LangChain handoffs 패턴(단일 에이전트 + middleware)으로 v1의 RAG + SQL + Supervisor 3에이전트를 대체하는 NCSHandoffAgent를 구현한다.

**Architecture:** 하나의 `create_agent(model, tools, state_schema, middleware)` 인스턴스가 `current_step` 상태에 따라 system_prompt와 tools를 동적으로 교체하는 3단계 순차 워크플로우 (`sql → rag → feedback`). v1의 `retrieve_context`, `query_employee_data` 도구는 그대로 재사용한다.

**Tech Stack:** langchain (AgentState, create_agent, wrap_model_call, ToolRuntime), langgraph (InMemorySaver, Command), Python 3.x, pytest-asyncio

---

## Task 1: config.py — agent_version 필드 추가

**Files:**
- Modify: `ai_server/config.py`

**Step 1: 현재 파일 읽기**

```
파일: ai_server/config.py
현재 필드: db_connection, spring_base_url, redis_host, redis_port, model_name, spring_api_version
```

**Step 2: agent_version 필드 추가**

`spring_api_version` 다음 줄에 추가:

```python
agent_version: str = "v1"
```

최종 파일:
```python
# ai_server/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_connection: str = "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db"
    spring_base_url: str = "http://localhost:8080"
    redis_host: str = "localhost"
    redis_port: int = 6379
    model_name: str = "gpt-4o-mini"
    spring_api_version: str = "v1"
    agent_version: str = "v1"


settings = Settings()
```

**Step 3: 확인**

```bash
cd ai_server
python -c "from config import settings; print(settings.agent_version)"
# 출력: v1
```

**Step 4: Commit**

```bash
git add ai_server/config.py
git commit -m "feat(config): agent_version 필드 추가 — AGENT_VERSION 환경변수로 v1/v2 선택

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: agents/v2/__init__.py 생성

**Files:**
- Create: `ai_server/agents/v2/__init__.py`

**Step 1: 빈 __init__.py 생성**

```python
# ai_server/agents/v2/__init__.py
```

(완전히 빈 파일 또는 최소 주석)

**Step 2: 디렉토리 구조 확인**

```bash
ls ai_server/agents/
# v1/  v2/  __init__.py  base.py  factory.py
```

**Step 3: Commit**

```bash
git add ai_server/agents/v2/__init__.py
git commit -m "feat(agents): v2 패키지 디렉토리 생성

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: agents/v2/supervisor.py — NCSHandoffAgent 구현

**Files:**
- Create: `ai_server/agents/v2/supervisor.py`

**Step 1: 테스트 파일 작성 (TDD)**

`ai_server/tests/test_agents.py` 파일 끝에 아래 테스트 추가:

```python
# ── v2 handoffs agent tests ──────────────────────────────────────

async def test_ncs_handoff_agent_step_config_has_three_steps():
    """STEP_CONFIG는 sql, rag, feedback 세 단계를 가진다."""
    from agents.v2.supervisor import STEP_CONFIG

    assert "sql" in STEP_CONFIG
    assert "rag" in STEP_CONFIG
    assert "feedback" in STEP_CONFIG

    for step, cfg in STEP_CONFIG.items():
        assert "prompt" in cfg
        assert "tools" in cfg


async def test_ncs_handoff_agent_sql_step_has_handoff_to_rag_tool():
    """sql 단계는 handoff_to_rag 도구를 포함한다."""
    from agents.v2.supervisor import STEP_CONFIG, handoff_to_rag

    sql_tools = STEP_CONFIG["sql"]["tools"]
    tool_names = [t.name for t in sql_tools]
    assert "handoff_to_rag" in tool_names


async def test_ncs_handoff_agent_rag_step_has_handoff_to_feedback_tool():
    """rag 단계는 handoff_to_feedback 도구를 포함한다."""
    from agents.v2.supervisor import STEP_CONFIG, handoff_to_feedback

    rag_tools = STEP_CONFIG["rag"]["tools"]
    tool_names = [t.name for t in rag_tools]
    assert "handoff_to_feedback" in tool_names


async def test_ncs_handoff_agent_feedback_step_has_no_tools():
    """feedback 단계는 도구가 없다."""
    from agents.v2.supervisor import STEP_CONFIG

    assert STEP_CONFIG["feedback"]["tools"] == []


async def test_ncs_handoff_agent_run_returns_message():
    """NCSHandoffAgent.run()은 마지막 메시지를 반환한다."""
    from agents.v2.supervisor import NCSHandoffAgent

    mock_rag_tools = []
    mock_sql_tools = []

    with patch("langchain.agents.create_agent") as mock_create, \
         patch("langchain.chat_models.init_chat_model"):

        mock_agent_instance = MagicMock()
        mock_agent_instance.astream.return_value = _async_iter([
            {"messages": [MagicMock(content="EMP001 종합 피드백 완료")]}
        ])
        mock_create.return_value = mock_agent_instance

        agent = NCSHandoffAgent(rag_tools=mock_rag_tools, sql_tools=mock_sql_tools)
        agent.create_agent()
        result = await agent.run(
            "EMP001의 NCS 과제 피드백",
            config={"configurable": {"thread_id": "test"}}
        )

    assert result is not None
    assert "EMP001" in result.content
```

**Step 2: 테스트 실행 — 실패 확인**

```bash
cd ai_server
python -m pytest tests/test_agents.py::test_ncs_handoff_agent_step_config_has_three_steps -v
# 출력: FAILED (ModuleNotFoundError: agents.v2.supervisor)
```

**Step 3: supervisor.py 구현**

```python
"""
ai_server/agents/v2/supervisor.py — NCS Handoffs Agent

LangChain handoffs 패턴 적용:
- 단일 create_agent 인스턴스
- current_step 상태에 따라 middleware가 system_prompt + tools 동적 교체
- 3단계 순차 워크플로우: sql → rag → feedback
"""
from typing import Literal, Callable

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.chat_models import init_chat_model
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from typing_extensions import NotRequired

from agents.base import BaseAgent
from config import settings


# ── 상태 스키마 ────────────────────────────────────────────────

NCSStep = Literal["sql", "rag", "feedback"]


class NCSAgentState(AgentState):
    """NCS 피드백 워크플로우 상태."""
    current_step: NotRequired[NCSStep]


# ── 핸드오프 도구 ──────────────────────────────────────────────

@tool
def handoff_to_rag(runtime: ToolRuntime[None, NCSAgentState]) -> Command:
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


@tool
def handoff_to_feedback(runtime: ToolRuntime[None, NCSAgentState]) -> Command:
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


# ── 단계별 프롬프트 ────────────────────────────────────────────

SQL_STEP_PROMPT = (
    "너는 NCS 직원 이력 조회 전문가야.\n"
    "사용자 메시지에서 사번(예: EMP001) 또는 직원 이름을 파악하여 "
    "query_employee_data 도구로 이력을 조회해.\n"
    "조회가 완료되면 반드시 handoff_to_rag 도구를 호출해서 NCS 문서 검색 단계로 전환해."
)

RAG_STEP_PROMPT = (
    "너는 NCS 문서 검색 전문가야.\n"
    "사용자 메시지와 이전 직원 이력 데이터를 참고해서 "
    "retrieve_context 도구로 관련 NCS 기준 문서를 검색해.\n"
    "검색이 완료되면 반드시 handoff_to_feedback 도구를 호출해서 피드백 생성 단계로 전환해."
)

FEEDBACK_STEP_PROMPT = (
    "너는 NCS 직원 관리 피드백 전문가야.\n"
    "이전 대화에서 수집된 직원 이력 데이터와 NCS 문서 검색 결과를 바탕으로 "
    "종합적이고 건설적인 피드백을 마크다운 형식으로 작성해줘.\n"
    "직원 이력과 NCS 기준을 항목별로 비교하고 구체적인 개선 방향을 제시해줘.\n"
    "불확실한 내용은 반드시 명시해."
)


# ── 단계별 설정 ────────────────────────────────────────────────

# STEP_CONFIG는 핸드오프 도구 정의 이후에 위치해야 한다.
# sql 단계의 tools는 factory에서 실제 도구를 주입할 때 확정된다.
# 여기서는 핸드오프 도구만 선언하고, 런타임 도구는 create_agent()에서 합산한다.

STEP_CONFIG: dict = {
    "sql": {
        "prompt": SQL_STEP_PROMPT,
        "tools": [],   # factory에서 sql_tools + [handoff_to_rag] 로 채워진다
    },
    "rag": {
        "prompt": RAG_STEP_PROMPT,
        "tools": [],   # factory에서 rag_tools + [handoff_to_feedback] 로 채워진다
    },
    "feedback": {
        "prompt": FEEDBACK_STEP_PROMPT,
        "tools": [],   # 최종 답변 생성, 도구 불필요
    },
}


# ── 미들웨어 ───────────────────────────────────────────────────

@wrap_model_call
def apply_ncs_step_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """current_step에 따라 system_prompt와 tools를 매 모델 호출 전에 교체한다."""
    current_step = request.state.get("current_step", "sql")
    config = STEP_CONFIG[current_step]
    request = request.override(
        system_prompt=config["prompt"],
        tools=config["tools"],
    )
    return handler(request)


# ── NCSHandoffAgent ────────────────────────────────────────────

class NCSHandoffAgent(BaseAgent):
    """handoffs 패턴 기반 NCS 피드백 에이전트.

    단일 create_agent 인스턴스가 current_step 상태에 따라
    sql → rag → feedback 3단계 순차 워크플로우를 수행한다.
    """

    def __init__(self, rag_tools: list, sql_tools: list, model_name: str = None):
        self.model = init_chat_model(model_name or settings.model_name)
        self._rag_tools = rag_tools
        self._sql_tools = sql_tools

    def create_agent(self, tools: list = None):
        # 단계별 도구 조합을 STEP_CONFIG에 주입
        STEP_CONFIG["sql"]["tools"] = self._sql_tools + [handoff_to_rag]
        STEP_CONFIG["rag"]["tools"] = self._rag_tools + [handoff_to_feedback]
        STEP_CONFIG["feedback"]["tools"] = []

        all_tools = self._sql_tools + self._rag_tools + [handoff_to_rag, handoff_to_feedback]

        self.agent = create_agent(
            self.model,
            tools=all_tools,
            state_schema=NCSAgentState,
            middleware=[apply_ncs_step_config],
            checkpointer=InMemorySaver(),
        )

    async def run(self, query: str, config: dict = None):
        if not hasattr(self, "agent"):
            raise ValueError("create_agent()를 먼저 호출하세요.")
        last_message = None
        async for event in self.agent.astream(
            {"messages": [{"role": "user", "content": query}]},
            config=config or {},
            stream_mode="values",
        ):
            last_message = event["messages"][-1]
        return last_message
```

**Step 4: 테스트 실행 — 통과 확인**

```bash
cd ai_server
python -m pytest tests/test_agents.py::test_ncs_handoff_agent_step_config_has_three_steps \
                 tests/test_agents.py::test_ncs_handoff_agent_sql_step_has_handoff_to_rag_tool \
                 tests/test_agents.py::test_ncs_handoff_agent_rag_step_has_handoff_to_feedback_tool \
                 tests/test_agents.py::test_ncs_handoff_agent_feedback_step_has_no_tools \
                 tests/test_agents.py::test_ncs_handoff_agent_run_returns_message \
                 -v
# 출력: 5 passed
```

**Step 5: Commit**

```bash
git add ai_server/agents/v2/supervisor.py ai_server/tests/test_agents.py
git commit -m "feat(agents/v2): NCSHandoffAgent — handoffs 패턴 3단계 순차 워크플로우

sql→rag→feedback, middleware 기반 동적 system_prompt/tools 교체.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: agents/factory.py — version 파라미터 추가

**Files:**
- Modify: `ai_server/agents/factory.py`

**Step 1: 테스트 추가**

`ai_server/tests/test_agents.py` 끝에 추가:

```python
async def test_create_agent_v2_returns_base_agent():
    """create_agent(vsm, version='v2')는 NCSHandoffAgent(BaseAgent)를 반환한다."""
    from agents.factory import create_agent
    from agents.base import BaseAgent

    mock_vsm = MagicMock()

    with patch("agents.factory.ToolBuilder") as mock_tb, \
         patch("agents.factory.SqlToolBuilder") as mock_sql_tb, \
         patch("agents.factory.NCSHandoffAgent") as mock_v2_cls, \
         patch("agents.factory.EmployeeClientV1") as mock_emp_cls:

        mock_tb.return_value.build_tools.return_value = []
        mock_sql_tb.return_value.build_tools.return_value = []

        mock_agent = MagicMock(spec=BaseAgent)
        mock_v2_cls.return_value = mock_agent

        result = await create_agent(mock_vsm, version="v2")

    assert isinstance(result, BaseAgent)
    mock_v2_cls.assert_called_once_with(
        rag_tools=[],
        sql_tools=[],
    )
    mock_agent.create_agent.assert_called_once()
```

**Step 2: 테스트 실행 — 실패 확인**

```bash
cd ai_server
python -m pytest tests/test_agents.py::test_create_agent_v2_returns_base_agent -v
# 출력: FAILED (create_agent() got an unexpected keyword argument 'version')
```

**Step 3: factory.py 수정**

```python
# ai_server/agents/factory.py
from agents.base import BaseAgent
from agents.v1.rag_agent import ChatAgent
from agents.v1.sql_agent import SqlAgent
from agents.v1.supervisor import SupervisorAgent
from tools.rag_tool import ToolBuilder
from tools.sql_tool import SqlToolBuilder
from clients.spring.v1.employee import EmployeeClientV1
from infra.vector_store import VectorStoreManager


async def create_agent(vsm: VectorStoreManager, version: str = "v1") -> BaseAgent:
    """VectorStoreManager를 받아 완전히 조립된 Agent를 반환한다.

    Args:
        vsm: VectorStoreManager 인스턴스
        version: 에이전트 버전 ("v1" | "v2"). 기본값 "v1".
    """
    if version == "v2":
        from agents.v2.supervisor import NCSHandoffAgent
        rag_tools = ToolBuilder(vsm).build_tools()
        employee_client = EmployeeClientV1()
        sql_tools = SqlToolBuilder(employee_client).build_tools()
        agent = NCSHandoffAgent(rag_tools=rag_tools, sql_tools=sql_tools)
        agent.create_agent()
        return agent

    # v1 기존 코드
    rag_tools = ToolBuilder(vsm).build_tools()

    rag_agent = ChatAgent()
    rag_agent.create_agent(rag_tools)

    employee_client = EmployeeClientV1()
    sql_agent = SqlAgent(employee_client=employee_client)
    sql_agent.create_agent()

    supervisor = SupervisorAgent(rag_agent=rag_agent, sql_agent=sql_agent)
    supervisor.create_agent()
    return supervisor
```

**Step 4: 기존 테스트도 통과하는지 확인**

```bash
cd ai_server
python -m pytest tests/test_agents.py -v
# 모든 테스트 PASS (기존 v1 테스트 포함)
```

**Step 5: Commit**

```bash
git add ai_server/agents/factory.py ai_server/tests/test_agents.py
git commit -m "feat(factory): version 파라미터 추가 — v2이면 NCSHandoffAgent 반환

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: server.py — version 전달

**Files:**
- Modify: `ai_server/server.py:51`

**Step 1: server.py의 create_agent 호출 수정**

기존 (line 51):
```python
agent = await create_agent(vector_store_manager)
```

변경 후:
```python
agent = await create_agent(vector_store_manager, version=settings.agent_version)
```

**Step 2: 확인 — 구문 오류 없음**

```bash
cd ai_server
python -c "import server"
# 출력: 오류 없음 (DB 연결 오류는 정상)
```

**Step 3: Commit**

```bash
git add ai_server/server.py
git commit -m "feat(server): AGENT_VERSION 환경변수로 v1/v2 에이전트 선택

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: .env에 AGENT_VERSION 추가 + 전체 테스트

**Step 1: .env 파일 확인 및 AGENT_VERSION 설정**

`.env` 파일에 다음 줄이 있는지 확인:
```
AGENT_VERSION=v1
```

없으면 추가. v2로 테스트하려면:
```
AGENT_VERSION=v2
```

**Step 2: 전체 테스트 실행**

```bash
cd ai_server
python -m pytest tests/ -v
# 출력: 모든 테스트 PASS
```

**Step 3: v2 에이전트 수동 E2E 확인 절차**

1. `.env`에 `AGENT_VERSION=v2` 설정
2. AI 서버 기동: `uvicorn server:app --reload --port 8000`
3. 서버 로그에서 "Agent 초기화 완료" 확인
4. curl로 테스트:

```bash
curl -s -X POST http://localhost:8000/internal/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "EMP001의 NCS 과제 피드백해줘",
    "doc_ids": [],
    "thread_id": "test-v2-001"
  }' | python -m json.tool
```

5. 응답에서 `answer` 필드가 3단계(sql→rag→feedback)를 거친 종합 피드백인지 확인

**Step 4: Commit**

```bash
git add .env
git commit -m "config: AGENT_VERSION=v1 기본값 설정 (.env)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 최종 파일 목록

| 파일 | 변경 |
|------|------|
| `ai_server/config.py` | `agent_version: str = "v1"` 추가 |
| `ai_server/agents/v2/__init__.py` | 신규 (빈 파일) |
| `ai_server/agents/v2/supervisor.py` | NCSHandoffAgent 전체 구현 |
| `ai_server/agents/factory.py` | `version` 파라미터 + v2 분기 |
| `ai_server/server.py` | `create_agent(..., version=settings.agent_version)` |
| `ai_server/tests/test_agents.py` | v2 테스트 5개 + factory v2 테스트 1개 추가 |
