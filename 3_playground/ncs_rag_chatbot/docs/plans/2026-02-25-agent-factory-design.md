# Agent Factory 설계 — server.py의 agent 단일 의존

**Goal:** `server.py`가 `BaseAgent` 인터페이스 하나와 `create_agent(vsm)` 팩토리만 알고, 내부 아키텍처(SupervisorAgent, ChatAgent, SqlAgent, ToolBuilder, EmployeeClientV1 등)를 완전히 모르게 한다.

---

## 문제

`server.py`가 내부 agent 아키텍처를 알고 있다:

```python
from agents import ChatAgent, SqlAgent, SupervisorAgent
from tools import ToolBuilder
from clients.spring import EmployeeClientV1

# lifespan에서 직접 조립
rag_agent = ChatAgent(); rag_agent.create_agent(rag_tools)
sql_agent = SqlAgent(employee_client=employee_client); sql_agent.create_agent()
supervisor_agent = SupervisorAgent(rag_agent=rag_agent, sql_agent=sql_agent)
supervisor_agent.create_agent()
```

v2에서 agent 아키텍처가 바뀌면 server.py도 함께 수정해야 한다.

---

## 해결: `agents/factory.py` + 팩토리 패턴

### 새 파일: `agents/factory.py`

모든 내부 조립 로직을 팩토리로 캡슐화:

```python
# agents/factory.py
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

### 수정: `agents/__init__.py`

공개 API를 `BaseAgent`와 `create_agent`만으로 축소:

```python
# agents/__init__.py
from agents.base import BaseAgent
from agents.factory import create_agent

__all__ = ["BaseAgent", "create_agent"]
```

### 수정: `server.py`

```python
# import — 단순화
from agents import create_agent, BaseAgent

# global
agent: Optional[BaseAgent] = None

# lifespan
agent = await create_agent(vector_store_manager)

# chat endpoint
last_message = await agent.run(req.query, config=config)
```

---

## 최종 server.py import 목록

```python
from infra.tracing import setup_tracing
from infra.embeddings import EmbeddingModel
from infra.vector_store import VectorStoreManager
from infra.ingest import ingest_single_document
from agents import create_agent, BaseAgent
from config import settings
```

`tools`, `clients`, `ChatAgent`, `SqlAgent`, `SupervisorAgent` — 모두 제거.

---

## v2 전환 시

`agents/factory.py`만 교체. `server.py`는 무변경.

---

## 원칙

- `server.py`는 `agents` 패키지의 공개 API(`create_agent`, `BaseAgent`)만 사용한다.
- 내부 아키텍처(어떤 sub-agent가 몇 개인지, 어떻게 연결되는지)는 `factory.py`가 캡슐화한다.
- `VectorStoreManager`는 server가 소유 (→ `_collect_sources`에도 사용).
