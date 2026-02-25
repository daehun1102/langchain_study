# Agent Factory Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `agents/factory.py`를 만들어 agent 조립 로직을 캡슐화하고, `server.py`가 `BaseAgent`와 `create_agent(vsm)` 하나만 알도록 한다.

**Architecture:** `agents/factory.py`에 `async create_agent(vsm) -> BaseAgent` 팩토리 함수를 추가. `agents/__init__.py`는 `BaseAgent`와 `create_agent`만 export. `server.py`는 agent 내부 구조(ChatAgent/SqlAgent/SupervisorAgent/ToolBuilder/EmployeeClientV1)를 일체 모르게 된다.

**Tech Stack:** Python 3.11, FastAPI, pytest-asyncio

---

## 사전 확인

```bash
cd 3_playground/ncs_rag_chatbot/ai_server
pytest eval/tests/ tests/ -v
# Expected: 39 passed
```

---

## Task 1: `agents/factory.py` 생성 + `agents/__init__.py` 업데이트

**Files:**
- Create: `ai_server/agents/factory.py`
- Modify: `ai_server/agents/__init__.py`
- Test: `ai_server/tests/test_agents.py`

**Step 1: 테스트 작성 (failing)**

`ai_server/tests/test_agents.py` 파일 끝에 추가:

```python
async def test_create_agent_returns_base_agent():
    """create_agent(vsm)는 BaseAgent를 반환해야 한다."""
    from agents.factory import create_agent
    from agents.base import BaseAgent

    mock_vsm = MagicMock()

    with patch("agents.factory.ToolBuilder") as mock_tb, \
         patch("agents.factory.ChatAgent") as mock_chat_cls, \
         patch("agents.factory.SqlAgent") as mock_sql_cls, \
         patch("agents.factory.SupervisorAgent") as mock_sup_cls, \
         patch("agents.factory.EmployeeClientV1") as mock_emp_cls:

        mock_tb.return_value.build_tools.return_value = []

        mock_chat = MagicMock(spec=BaseAgent)
        mock_chat_cls.return_value = mock_chat

        mock_sql = MagicMock(spec=BaseAgent)
        mock_sql_cls.return_value = mock_sql

        mock_sup = MagicMock(spec=BaseAgent)
        mock_sup_cls.return_value = mock_sup

        result = await create_agent(mock_vsm)

    assert isinstance(result, BaseAgent)
    mock_tb.assert_called_once_with(mock_vsm)
    mock_chat.create_agent.assert_called_once_with([])
    mock_sql.create_agent.assert_called_once()
    mock_sup.create_agent.assert_called_once()
```

**Step 2: 테스트 실행 — FAIL 확인**

```bash
cd 3_playground/ncs_rag_chatbot/ai_server
pytest tests/test_agents.py::test_create_agent_returns_base_agent -v
# Expected: FAIL — ModuleNotFoundError: No module named 'agents.factory'
```

**Step 3: `agents/factory.py` 생성**

```python
# ai_server/agents/factory.py
from agents.base import BaseAgent
from agents.v1.rag_agent import ChatAgent
from agents.v1.sql_agent import SqlAgent
from agents.v1.supervisor import SupervisorAgent
from tools.rag_tool import ToolBuilder
from clients.spring.v1.employee import EmployeeClientV1


async def create_agent(vsm) -> BaseAgent:
    """VectorStoreManager를 받아 완전히 조립된 Agent를 반환한다."""
    tool_builder = ToolBuilder(vsm)
    rag_tools = tool_builder.build_tools()

    rag_agent = ChatAgent()
    rag_agent.create_agent(rag_tools)

    employee_client = EmployeeClientV1()
    sql_agent = SqlAgent(employee_client=employee_client)
    sql_agent.create_agent()

    supervisor = SupervisorAgent(rag_agent=rag_agent, sql_agent=sql_agent)
    supervisor.create_agent()
    return supervisor
```

**Step 4: `agents/__init__.py` 업데이트**

현재:
```python
from agents.v1.rag_agent import ChatAgent
from agents.v1.sql_agent import SqlAgent
from agents.v1.supervisor import SupervisorAgent

__all__ = ["ChatAgent", "SqlAgent", "SupervisorAgent"]
```

교체:
```python
from agents.base import BaseAgent
from agents.factory import create_agent

__all__ = ["BaseAgent", "create_agent"]
```

**Step 5: 테스트 실행 — PASS 확인**

```bash
pytest tests/test_agents.py -v
# Expected: 4 passed (기존 3 + 신규 1)
```

**Step 6: 전체 테스트 확인**

```bash
pytest eval/tests/ tests/ -v 2>&1 | tail -5
# Expected: 39 passed
```

**Step 7: 커밋**

```bash
git add ai_server/agents/factory.py ai_server/agents/__init__.py ai_server/tests/test_agents.py
git commit -m "feat(agents): factory.py 추가 — create_agent(vsm) → BaseAgent 캡슐화"
```

---

## Task 2: `server.py` 업데이트

**Files:**
- Modify: `ai_server/server.py`

**Step 1: 현재 상태 확인**

```bash
grep -n "from agents\|from tools\|from clients\|supervisor_agent\|rag_agent\|sql_agent\|tool_builder\|employee_client" ai_server/server.py
```

Expected:
```
34: from agents import ChatAgent, SqlAgent, SupervisorAgent
35: from tools import ToolBuilder
36: from clients.spring import EmployeeClientV1
42: supervisor_agent: Optional[SupervisorAgent] = None
48:     global vector_store_manager, supervisor_agent
53:     tool_builder = ToolBuilder(vector_store_manager)
54:     rag_tools = tool_builder.build_tools()
55:     rag_agent = ChatAgent()
56:     rag_agent.create_agent(rag_tools)
59:     employee_client = EmployeeClientV1()
60:     sql_agent = SqlAgent(employee_client=employee_client)
61:     sql_agent.create_agent()
64:     supervisor_agent = SupervisorAgent(rag_agent=rag_agent, sql_agent=sql_agent)
65:     supervisor_agent.create_agent()
158:         last_message = await supervisor_agent.run(req.query, config=config)
```

**Step 2: `server.py` import 교체 (lines 34-36)**

```python
# Before
from agents import ChatAgent, SqlAgent, SupervisorAgent
from tools import ToolBuilder
from clients.spring import EmployeeClientV1

# After
from agents import create_agent, BaseAgent
```

**Step 3: global 변수 교체 (line 41-42)**

```python
# Before
supervisor_agent: Optional[SupervisorAgent] = None

# After
agent: Optional[BaseAgent] = None
```

**Step 4: lifespan 내 agent 조립 로직 교체 (lines 48-68)**

```python
# Before
@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store_manager, supervisor_agent

    emb = EmbeddingModel().get_embeddings()
    vector_store_manager = await VectorStoreManager.create(settings.db_connection, emb)

    # RAG Agent
    tool_builder = ToolBuilder(vector_store_manager)
    rag_tools = tool_builder.build_tools()
    rag_agent = ChatAgent()
    rag_agent.create_agent(rag_tools)

    # SQL Agent
    employee_client = EmployeeClientV1()
    sql_agent = SqlAgent(employee_client=employee_client)
    sql_agent.create_agent()

    # Supervisor
    supervisor_agent = SupervisorAgent(rag_agent=rag_agent, sql_agent=sql_agent)
    supervisor_agent.create_agent()

    logger.info("[server] SupervisorAgent 초기화 완료")
    yield

# After
@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store_manager, agent

    emb = EmbeddingModel().get_embeddings()
    vector_store_manager = await VectorStoreManager.create(settings.db_connection, emb)

    agent = await create_agent(vector_store_manager)

    logger.info("[server] Agent 초기화 완료")
    yield
```

**Step 5: chat endpoint 내 `supervisor_agent` → `agent` 교체 (line 158)**

```python
# Before
last_message = await supervisor_agent.run(req.query, config=config)

# After
last_message = await agent.run(req.query, config=config)
```

**Step 6: server.py에 v1/버전 참조가 남아있지 않은지 확인**

```bash
grep -n "v1\|ChatAgent\|SqlAgent\|SupervisorAgent\|ToolBuilder\|EmployeeClientV1\|supervisor_agent" ai_server/server.py
# Expected: (출력 없음)
```

**Step 7: 전체 테스트 확인**

```bash
pytest eval/tests/ tests/ -v 2>&1 | tail -5
# Expected: 39 passed
```

**Step 8: 커밋**

```bash
git add ai_server/server.py
git commit -m "refactor(server): agent 단일 의존 — create_agent/BaseAgent만 사용"
```
