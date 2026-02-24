# Multi-Agent System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 기존 RAG Agent를 유지하면서 SQL Agent를 추가하고, Supervisor Agent가 LLM 기반으로 두 서브에이전트를 라우팅하는 멀티에이전트 시스템을 구축한다.

**Architecture:** Supervisor Agent(`create_agent`)가 `call_rag_agent`, `call_sql_agent` 두 개의 `@tool`을 통해 서브에이전트를 순차 호출한다. SQL Agent는 Spring API(`httpx`)를 통해 Oracle LMS DB를 조회한다. `ai_server/`는 `agents/`, `tools/`, `clients/`, `infra/` 로 역할별 분리된다.

**Tech Stack:** Python 3.11, FastAPI, LangChain v1, LangGraph v1, `create_agent`, `@tool`, `RunnableConfig`, `InMemorySaver`, `httpx`, `pydantic-settings`, Oracle SQL

---

## 사전 확인

```bash
cd ai_server
pytest eval/tests/ -v   # 기존 테스트 모두 PASS 확인
```

---

## Task 1: config.py — 환경변수 중앙 관리

**Files:**
- Create: `ai_server/config.py`
- Create: `ai_server/tests/__init__.py`
- Create: `ai_server/tests/test_config.py`

**Step 1: 실패하는 테스트 작성**

```python
# ai_server/tests/test_config.py
import os
from unittest.mock import patch

def test_settings_default_values():
    from config import settings
    assert settings.spring_base_url == "http://localhost:8080"
    assert settings.redis_port == 6379
    assert settings.model_name == "gpt-4o-mini"
    assert settings.spring_api_version == "v1"

def test_settings_from_env():
    with patch.dict(os.environ, {"SPRING_BASE_URL": "http://spring:8080"}):
        import importlib, config
        importlib.reload(config)
        from config import settings
        assert settings.spring_base_url == "http://spring:8080"
```

**Step 2: 테스트 실행 — FAIL 확인**

```bash
cd ai_server && pytest tests/test_config.py -v
# Expected: ERROR (config module not found)
```

**Step 3: config.py 구현**

```python
# ai_server/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_connection: str = "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db"
    spring_base_url: str = "http://localhost:8080"
    redis_host: str = "localhost"
    redis_port: int = 6379
    model_name: str = "gpt-4o-mini"
    spring_api_version: str = "v1"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
```

**Step 4: 테스트 실행 — PASS 확인**

```bash
pytest tests/test_config.py -v
# Expected: 2 passed
```

**Step 5: 커밋**

```bash
git add ai_server/config.py ai_server/tests/__init__.py ai_server/tests/test_config.py
git commit -m "feat(config): 환경변수 중앙 관리 config.py 추가"
```

---

## Task 2: infra/ 디렉토리 — 인프라 파일 이동

**Files:**
- Create: `ai_server/infra/__init__.py`
- Create: `ai_server/infra/embeddings.py` (기존 내용 복사)
- Create: `ai_server/infra/vector_store.py` (기존 내용 복사)
- Create: `ai_server/infra/prompt_loader.py` (기존 내용 복사)
- Create: `ai_server/infra/tracing.py` (기존 내용 복사)
- Modify: `ai_server/embeddings.py` → shim으로 교체 (기존 eval imports 호환)
- Modify: `ai_server/vector_store.py` → shim
- Modify: `ai_server/prompt_loader.py` → shim
- Modify: `ai_server/tracing.py` → shim

**Step 1: infra/ 파일 생성**

기존 각 파일 내용을 `infra/` 아래로 복사한다.
단, `infra/prompt_loader.py`에서 `config.py` 활용하도록 수정:

```python
# ai_server/infra/prompt_loader.py
# (기존 내용 그대로 복사, REDIS_HOST/PORT를 config에서 읽도록 수정)
import os
import redis
from config import settings

REDIS_HOST = settings.redis_host
REDIS_PORT = settings.redis_port
PREFIX = "prompt:"
# ... (나머지 FALLBACK_PROMPTS, get_prompt 동일)
```

`infra/__init__.py`:
```python
# ai_server/infra/__init__.py
from infra.embeddings import EmbeddingModel
from infra.vector_store import VectorStoreManager
from infra.prompt_loader import get_prompt
from infra.tracing import setup_tracing

__all__ = ["EmbeddingModel", "VectorStoreManager", "get_prompt", "setup_tracing"]
```

**Step 2: 기존 파일을 shim으로 교체**

```python
# ai_server/embeddings.py  (shim — eval/tasks.py 하위호환)
from infra.embeddings import EmbeddingModel  # noqa: F401
```

```python
# ai_server/vector_store.py  (shim)
from infra.vector_store import VectorStoreManager  # noqa: F401
```

```python
# ai_server/prompt_loader.py  (shim)
from infra.prompt_loader import get_prompt, FALLBACK_PROMPTS  # noqa: F401
```

```python
# ai_server/tracing.py  (shim)
from infra.tracing import setup_tracing  # noqa: F401
```

**Step 3: 기존 테스트 PASS 확인**

```bash
pytest eval/tests/ -v
# Expected: 모두 PASS (shim 덕분에 기존 imports 유지)
```

**Step 4: 커밋**

```bash
git add ai_server/infra/ ai_server/embeddings.py ai_server/vector_store.py \
        ai_server/prompt_loader.py ai_server/tracing.py
git commit -m "refactor(infra): 인프라 파일 infra/ 디렉토리로 그룹화"
```

---

## Task 3: tools/ 디렉토리 — RAG Tool 이동

**Files:**
- Create: `ai_server/tools/__init__.py`
- Create: `ai_server/tools/rag_tool.py` (기존 tool.py 내용 복사 + import 수정)
- Modify: `ai_server/tool.py` → shim

**Step 1: tools/rag_tool.py 생성**

기존 `tool.py` 내용을 그대로 복사하되 import 경로 수정:

```python
# ai_server/tools/rag_tool.py
"""
rag_tool.py — RAG 검색 도구
(기존 tool.py에서 이동)
"""
from langchain.tools import tool
from langchain_core.tools import Tool
from langchain_core.runnables import RunnableConfig
from typing import List, Optional


class ToolBuilder:

    def __init__(self, vector_store_manager):
        self.vsm = vector_store_manager

    def build_tools(self, k: int = 4) -> List[Tool]:
        vsm = self.vsm
        _k = k

        @tool(response_format="content_and_artifact")
        async def retrieve_context(query: str, config: RunnableConfig):
            """NCS 문서에서 질의와 관련된 내용을 검색한다."""
            doc_ids = config["configurable"].get("doc_ids", [])
            retrieved_docs = await vsm.similarity_search_by_doc_ids(
                query, doc_ids=doc_ids, k=_k
            )
            if not retrieved_docs:
                return "관련 문서를 찾을 수 없습니다.", []
            serialized = "\n\n".join(
                f"[doc_id: {doc.metadata.get('doc_id', 'unknown')}, "
                f"page: {doc.metadata.get('page', 0)}]\n{doc.page_content}"
                for doc in retrieved_docs
            )
            return serialized, retrieved_docs

        return [retrieve_context]
```

`tools/__init__.py`:
```python
from tools.rag_tool import ToolBuilder
from tools.sql_tool import SqlToolBuilder  # Task 5에서 추가

__all__ = ["ToolBuilder", "SqlToolBuilder"]
```

**Step 2: tool.py shim으로 교체**

```python
# ai_server/tool.py  (shim)
from tools.rag_tool import ToolBuilder  # noqa: F401
```

**Step 3: 기존 테스트 PASS 확인**

```bash
pytest eval/tests/ -v
```

**Step 4: 커밋**

```bash
git add ai_server/tools/ ai_server/tool.py
git commit -m "refactor(tools): RAG tool tools/ 디렉토리로 이동"
```

---

## Task 4: clients/ — Spring API HTTP 클라이언트

**Files:**
- Create: `ai_server/clients/__init__.py`
- Create: `ai_server/clients/spring/__init__.py`
- Create: `ai_server/clients/spring/base.py`
- Create: `ai_server/clients/spring/v1/__init__.py`
- Create: `ai_server/clients/spring/v1/employee.py`
- Create: `ai_server/tests/test_spring_client.py`

**Step 1: 실패하는 테스트 작성**

```python
# ai_server/tests/test_spring_client.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


async def test_get_history_returns_employee_data():
    from clients.spring.v1.employee import EmployeeClientV1

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "employee": {"employeeId": "EMP001", "name": "홍길동"},
        "educationHistory": [],
        "assignmentSubmissions": [],
        "gradingResults": [],
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        client = EmployeeClientV1(base_url="http://localhost:8080")
        result = await client.get_history("EMP001")

    assert result["employee"]["name"] == "홍길동"
    assert "educationHistory" in result


async def test_get_history_raises_on_http_error():
    from clients.spring.v1.employee import EmployeeClientV1

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock()
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        client = EmployeeClientV1(base_url="http://localhost:8080")
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_history("INVALID")
```

**Step 2: 테스트 실행 — FAIL 확인**

```bash
pytest tests/test_spring_client.py -v
# Expected: ERROR (module not found)
```

**Step 3: clients/ 구현**

```python
# ai_server/clients/spring/base.py
import httpx
from config import settings


class SpringClient:
    """Spring Boot API 공통 httpx 클라이언트."""

    def __init__(self, base_url: str = None, timeout: float = 10.0):
        self.base_url = base_url or settings.spring_base_url
        self.timeout = timeout

    def build(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
```

```python
# ai_server/clients/spring/v1/employee.py
import httpx
from typing import Any


class EmployeeClientV1:
    """직원 이력 API v1 클라이언트."""

    def __init__(self, base_url: str = None):
        from clients.spring.base import SpringClient
        self._spring = SpringClient(base_url=base_url)

    async def get_history(self, identifier: str) -> dict[str, Any]:
        """사번 또는 이름으로 직원 교육 이수/과제/채점 이력을 조회한다.

        Args:
            identifier: 사번(EMP001) 또는 이름(홍길동)
        Returns:
            {employee, educationHistory, assignmentSubmissions, gradingResults}
        """
        async with self._spring.build() as client:
            resp = await client.get(
                "/internal/v1/employee/history",
                params={"identifier": identifier},
            )
            resp.raise_for_status()
            return resp.json()
```

```python
# ai_server/clients/__init__.py
# 클라이언트 버전은 clients/spring/v1/ 내에서 관리
```

```python
# ai_server/clients/spring/__init__.py
from clients.spring.v1.employee import EmployeeClientV1

__all__ = ["EmployeeClientV1"]
```

```python
# ai_server/clients/spring/v1/__init__.py
from clients.spring.v1.employee import EmployeeClientV1

__all__ = ["EmployeeClientV1"]
```

**Step 4: 테스트 실행 — PASS 확인**

```bash
pytest tests/test_spring_client.py -v
# Expected: 2 passed
```

**Step 5: 커밋**

```bash
git add ai_server/clients/ ai_server/tests/test_spring_client.py
git commit -m "feat(clients): Spring API v1 Employee 클라이언트 추가"
```

---

## Task 5: tools/sql_tool.py — SQL 조회 Tool

**Files:**
- Create: `ai_server/tools/sql_tool.py`
- Create: `ai_server/tests/test_sql_tool.py`
- Modify: `ai_server/tools/__init__.py` (SqlToolBuilder import 추가)

**Step 1: 실패하는 테스트 작성**

```python
# ai_server/tests/test_sql_tool.py
import json
import pytest
from unittest.mock import AsyncMock


async def test_query_employee_data_returns_json():
    from clients.spring.v1.employee import EmployeeClientV1
    from tools.sql_tool import SqlToolBuilder

    mock_client = AsyncMock(spec=EmployeeClientV1)
    mock_client.get_history.return_value = {
        "employee": {"employeeId": "EMP001", "name": "홍길동"},
        "educationHistory": [{"courseName": "Python 기초", "score": 95.0}],
        "assignmentSubmissions": [],
        "gradingResults": [],
    }

    builder = SqlToolBuilder(employee_client=mock_client)
    tools = builder.build_tools()
    assert len(tools) == 1

    tool = tools[0]
    result = await tool.ainvoke({"identifier": "EMP001"})
    data = json.loads(result)
    assert data["employee"]["name"] == "홍길동"
    assert data["educationHistory"][0]["score"] == 95.0
    mock_client.get_history.assert_called_once_with("EMP001")


async def test_query_employee_data_handles_api_error():
    import httpx
    from clients.spring.v1.employee import EmployeeClientV1
    from tools.sql_tool import SqlToolBuilder

    mock_client = AsyncMock(spec=EmployeeClientV1)
    mock_client.get_history.side_effect = httpx.HTTPStatusError(
        "404", request=AsyncMock(), response=AsyncMock()
    )

    builder = SqlToolBuilder(employee_client=mock_client)
    tools = builder.build_tools()
    result = await tools[0].ainvoke({"identifier": "INVALID"})
    assert "조회 실패" in result
```

**Step 2: 테스트 실행 — FAIL 확인**

```bash
pytest tests/test_sql_tool.py -v
# Expected: ERROR (module not found)
```

**Step 3: sql_tool.py 구현**

```python
# ai_server/tools/sql_tool.py
"""
sql_tool.py — 직원 이력 조회 Tool (thin wrapper)

실제 HTTP 호출은 clients/spring/v1/employee.py 에 위임한다.
"""
import json
import logging
from typing import List

from langchain.tools import tool
from langchain_core.tools import Tool

logger = logging.getLogger("sql_tool")


class SqlToolBuilder:

    def __init__(self, employee_client):
        self._client = employee_client

    def build_tools(self) -> List[Tool]:
        _client = self._client

        @tool
        async def query_employee_data(identifier: str) -> str:
            """직원의 교육 이수 내역, 과제 제출, 채점 결과를 조회한다.

            Args:
                identifier: 사번(예: EMP001) 또는 직원 이름(예: 홍길동)
            Returns:
                JSON 형식의 직원 이력 데이터
            """
            try:
                result = await _client.get_history(identifier)
                return json.dumps(result, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error("[sql_tool] 직원 이력 조회 실패: %s", e)
                return f"직원 이력 조회 실패: {identifier} — {e}"

        return [query_employee_data]
```

**Step 4: tools/__init__.py 업데이트**

```python
# ai_server/tools/__init__.py
from tools.rag_tool import ToolBuilder
from tools.sql_tool import SqlToolBuilder

__all__ = ["ToolBuilder", "SqlToolBuilder"]
```

**Step 5: 테스트 실행 — PASS 확인**

```bash
pytest tests/test_sql_tool.py -v
# Expected: 2 passed
```

**Step 6: 커밋**

```bash
git add ai_server/tools/sql_tool.py ai_server/tools/__init__.py \
        ai_server/tests/test_sql_tool.py
git commit -m "feat(tools): SQL 직원 이력 조회 tool 추가"
```

---

## Task 6: agents/ 구조 — BaseAgent + RagAgent 이동

**Files:**
- Create: `ai_server/agents/__init__.py`
- Create: `ai_server/agents/base.py`
- Create: `ai_server/agents/v1/__init__.py`
- Create: `ai_server/agents/v1/rag_agent.py` (agent.py 내용 이동 + singleton 패턴 적용)
- Modify: `ai_server/agent.py` → shim

**Step 1: base.py 생성**

```python
# ai_server/agents/base.py
from abc import ABC, abstractmethod


class BaseAgent(ABC):

    @abstractmethod
    def create_agent(self, tools: list): ...

    @abstractmethod
    async def run(self, query: str, config: dict = None): ...
```

**Step 2: rag_agent.py 생성 (singleton + RunnableConfig 패턴 적용)**

> 참고: `docs/plans/2026-02-23-agent-improvement-design.md` — RunnableConfig 주입 방식

```python
# ai_server/agents/v1/rag_agent.py
"""
rag_agent.py — NCS 문서 검색 전문 에이전트

변경:
- agent.py에서 이동
- InMemorySaver checkpointer로 multi-turn 지원
- RunnableConfig로 doc_ids 런타임 주입 (rag_tool.py의 retrieve_context가 읽음)
"""
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig
from agents.base import BaseAgent
from infra.prompt_loader import get_prompt
from typing import List


PROMPT_KEYS = [
    "agent_system_prompt",
    "answer_format_prompt",
    "no_document_prompt",
    "query_enhance_prompt",
    "category_hint_prompt",
]


def _build_system_prompt() -> str:
    parts = [p for k in PROMPT_KEYS if (p := get_prompt(k))]
    return "\n\n".join(parts)


class ChatAgent(BaseAgent):

    def __init__(self, model_name: str = "gpt-4o-mini", system_prompt: str = None):
        self.model = init_chat_model(model_name)
        self.checkpointer = InMemorySaver()
        self.system_prompt = system_prompt if system_prompt is not None else _build_system_prompt()

    def create_agent(self, tools: List):
        self.agent = create_agent(
            self.model,
            tools,
            system_prompt=self.system_prompt,
            checkpointer=self.checkpointer,
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

**Step 3: agent.py shim으로 교체**

```python
# ai_server/agent.py  (shim — eval/tasks.py 하위호환)
from agents.v1.rag_agent import ChatAgent, PROMPT_KEYS, _build_system_prompt  # noqa: F401
```

**Step 4: agents/__init__.py 생성**

```python
# ai_server/agents/__init__.py
from agents.v1.rag_agent import ChatAgent

__all__ = ["ChatAgent"]
```

**Step 5: 기존 테스트 PASS 확인**

```bash
pytest eval/tests/ -v
# Expected: 모두 PASS (shim 유지)
```

**Step 6: 커밋**

```bash
git add ai_server/agents/ ai_server/agent.py
git commit -m "refactor(agents): RagAgent agents/v1/ 로 이동, singleton+RunnableConfig 적용"
```

---

## Task 7: agents/v1/sql_agent.py — SQL 에이전트

**Files:**
- Create: `ai_server/agents/v1/sql_agent.py`
- Create: `ai_server/tests/test_agents.py`

**Step 1: 실패하는 테스트 작성**

```python
# ai_server/tests/test_agents.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


async def test_sql_agent_run_returns_message():
    from agents.v1.sql_agent import SqlAgent
    from clients.spring.v1.employee import EmployeeClientV1

    mock_client = AsyncMock(spec=EmployeeClientV1)
    mock_client.get_history.return_value = {
        "employee": {"employeeId": "EMP001", "name": "홍길동"},
        "educationHistory": [],
        "assignmentSubmissions": [],
        "gradingResults": [],
    }

    with patch("langchain.chat_models.init_chat_model") as mock_model, \
         patch("langchain.agents.create_agent") as mock_create:

        mock_agent = AsyncMock()
        mock_agent.astream.return_value = _async_iter([
            {"messages": [MagicMock(content="홍길동의 이력 조회 완료")]}
        ])
        mock_create.return_value = mock_agent
        mock_model.return_value = MagicMock()

        agent = SqlAgent(employee_client=mock_client)
        agent.create_agent()
        result = await agent.run("EMP001 이력 조회")

    assert result.content == "홍길동의 이력 조회 완료"


async def _async_iter(items):
    for item in items:
        yield item
```

**Step 2: 테스트 실행 — FAIL 확인**

```bash
pytest tests/test_agents.py::test_sql_agent_run_returns_message -v
```

**Step 3: sql_agent.py 구현**

```python
# ai_server/agents/v1/sql_agent.py
"""
sql_agent.py — 직원 이력 조회 전문 에이전트
"""
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from agents.base import BaseAgent
from tools.sql_tool import SqlToolBuilder
from config import settings

SQL_SYSTEM_PROMPT = (
    "너는 직원의 NCS 교육 이수 내역을 조회하는 전문가야.\n"
    "사용자가 직원 정보를 요청하면 반드시 query_employee_data 도구를 사용해서 조회해줘.\n"
    "identifier는 사번(예: EMP001) 또는 직원 이름(예: 홍길동) 중 질문에서 파악되는 값을 사용해.\n"
    "조회 결과를 한국어로 알기 쉽게 정리해서 답변해줘."
)


class SqlAgent(BaseAgent):

    def __init__(self, employee_client, model_name: str = None):
        self.model = init_chat_model(model_name or settings.model_name)
        self.checkpointer = InMemorySaver()
        self.system_prompt = SQL_SYSTEM_PROMPT
        tool_builder = SqlToolBuilder(employee_client)
        self._tools = tool_builder.build_tools()

    def create_agent(self):
        self.agent = create_agent(
            self.model,
            self._tools,
            system_prompt=self.system_prompt,
            checkpointer=self.checkpointer,
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

**Step 4: agents/__init__.py 업데이트**

```python
# ai_server/agents/__init__.py
from agents.v1.rag_agent import ChatAgent
from agents.v1.sql_agent import SqlAgent

__all__ = ["ChatAgent", "SqlAgent"]
```

**Step 5: 테스트 실행 — PASS 확인**

```bash
pytest tests/test_agents.py::test_sql_agent_run_returns_message -v
```

**Step 6: 커밋**

```bash
git add ai_server/agents/v1/sql_agent.py ai_server/agents/__init__.py \
        ai_server/tests/test_agents.py
git commit -m "feat(agents): SQL Agent 추가 (직원 이력 조회 전문)"
```

---

## Task 8: agents/v1/supervisor.py — Supervisor Agent

**Files:**
- Create: `ai_server/agents/v1/supervisor.py`
- Modify: `ai_server/tests/test_agents.py` (supervisor 테스트 추가)
- Modify: `ai_server/agents/__init__.py`

**Step 1: 실패하는 테스트 추가**

`ai_server/tests/test_agents.py`에 추가:

```python
async def test_supervisor_routes_to_sql_agent_for_employee_query():
    """사번 포함 질문은 call_sql_agent tool을 호출한다."""
    from agents.v1.supervisor import SupervisorAgent
    from agents.v1.rag_agent import ChatAgent
    from agents.v1.sql_agent import SqlAgent

    mock_rag = AsyncMock(spec=ChatAgent)
    mock_sql = AsyncMock(spec=SqlAgent)

    with patch("langchain.chat_models.init_chat_model") as mock_model, \
         patch("langchain.agents.create_agent") as mock_create:

        mock_agent = AsyncMock()
        mock_agent.astream.return_value = _async_iter([
            {"messages": [MagicMock(content="EMP001 홍길동의 교육 이수 완료")]}
        ])
        mock_create.return_value = mock_agent
        mock_model.return_value = MagicMock()

        supervisor = SupervisorAgent(rag_agent=mock_rag, sql_agent=mock_sql)
        supervisor.create_agent()
        result = await supervisor.run(
            "EMP001 직원의 이수 내역 알려줘",
            config={"configurable": {"thread_id": "test-thread"}}
        )

    assert result is not None
    assert "EMP001" in result.content


async def test_supervisor_has_two_tools():
    """Supervisor는 call_rag_agent와 call_sql_agent 두 도구를 가진다."""
    from agents.v1.supervisor import SupervisorAgent, _build_supervisor_tools

    mock_rag = AsyncMock()
    mock_sql = AsyncMock()
    tools = _build_supervisor_tools(mock_rag, mock_sql)

    tool_names = [t.name for t in tools]
    assert "call_rag_agent" in tool_names
    assert "call_sql_agent" in tool_names
```

**Step 2: 테스트 실행 — FAIL 확인**

```bash
pytest tests/test_agents.py::test_supervisor_has_two_tools -v
```

**Step 3: supervisor.py 구현**

```python
# ai_server/agents/v1/supervisor.py
"""
supervisor.py — NCS 관리 감독관 Supervisor Agent

RAG Agent와 SQL Agent를 @tool로 래핑하여 LLM 기반 라우팅을 수행한다.
순차 처리 원칙: SQL 조회가 필요하면 먼저 실행 후, 결과를 컨텍스트에 포함해 RAG 호출.
"""
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from agents.base import BaseAgent
from config import settings
from typing import List

SUPERVISOR_SYSTEM_PROMPT = (
    "너는 NCS(국가직무능력표준) 직원 관리 감독관 AI야.\n\n"
    "## 도구 사용 규칙\n"
    "1. 질문에 사번(예: EMP001) 또는 직원 이름이 포함되어 있으면 → call_sql_agent를 먼저 호출\n"
    "2. NCS 기준, 직무능력, 교육과정 내용이 필요하면 → call_rag_agent를 호출\n"
    "3. 두 정보가 모두 필요한 경우 → call_sql_agent 먼저 실행, "
    "그 결과를 포함하여 call_rag_agent 호출\n"
    "4. 두 도구의 결과를 통합하여 명확한 최종 답변을 생성\n\n"
    "## 답변 원칙\n"
    "- 마크다운 형식으로 작성\n"
    "- 직원 이력과 NCS 기준을 비교할 때는 항목별로 명확히 구분\n"
    "- 불확실한 내용은 반드시 명시"
)


def _build_supervisor_tools(rag_agent, sql_agent) -> List:
    """서브에이전트를 @tool로 래핑하여 반환한다."""
    _rag = rag_agent
    _sql = sql_agent

    @tool
    async def call_rag_agent(query: str, config: RunnableConfig) -> str:
        """NCS 문서에서 관련 내용을 검색하여 답변한다.
        NCS 기준, 직무능력, 교육과정 내용에 관한 질문에 사용한다."""
        result = await _rag.run(query, config=config)
        return result.content if result else "RAG 에이전트 응답 없음"

    @tool
    async def call_sql_agent(query: str, config: RunnableConfig) -> str:
        """직원의 교육 이수 내역, 과제 제출, 채점 결과를 조회하여 답변한다.
        사번 또는 직원 이름이 포함된 질문에 사용한다."""
        result = await _sql.run(query, config=config)
        return result.content if result else "SQL 에이전트 응답 없음"

    return [call_rag_agent, call_sql_agent]


class SupervisorAgent(BaseAgent):

    def __init__(self, rag_agent, sql_agent, model_name: str = None):
        self.model = init_chat_model(model_name or settings.model_name)
        self.checkpointer = InMemorySaver()
        self.system_prompt = SUPERVISOR_SYSTEM_PROMPT
        self._tools = _build_supervisor_tools(rag_agent, sql_agent)

    def create_agent(self, tools: list = None):
        self.agent = create_agent(
            self.model,
            tools or self._tools,
            system_prompt=self.system_prompt,
            checkpointer=self.checkpointer,
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

**Step 4: agents/__init__.py 최종 업데이트**

```python
# ai_server/agents/__init__.py
from agents.v1.rag_agent import ChatAgent
from agents.v1.sql_agent import SqlAgent
from agents.v1.supervisor import SupervisorAgent

__all__ = ["ChatAgent", "SqlAgent", "SupervisorAgent"]
```

**Step 5: 테스트 실행 — PASS 확인**

```bash
pytest tests/test_agents.py -v
# Expected: 모두 PASS
```

**Step 6: 커밋**

```bash
git add ai_server/agents/v1/supervisor.py ai_server/agents/__init__.py \
        ai_server/tests/test_agents.py
git commit -m "feat(agents): Supervisor Agent 추가 (LLM 기반 라우팅)"
```

---

## Task 9: server.py — Supervisor로 교체

**Files:**
- Modify: `ai_server/server.py`

**Step 1: server.py 전체 수정**

기존 `server.py`에서 변경되는 부분:

```python
# 변경: import 경로
from infra.tracing import setup_tracing
setup_tracing()

from infra.embeddings import EmbeddingModel
from infra.vector_store import VectorStoreManager
from agents.v1.rag_agent import ChatAgent
from agents.v1.sql_agent import SqlAgent
from agents.v1.supervisor import SupervisorAgent
from tools.rag_tool import ToolBuilder
from clients.spring.v1.employee import EmployeeClientV1
from config import settings

# 변경: 전역 변수
vector_store_manager: Optional[VectorStoreManager] = None
supervisor_agent: Optional[SupervisorAgent] = None

# 변경: lifespan — Supervisor 싱글턴 생성
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

# 변경: ChatRequest에 thread_id 추가
class ChatRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None
    thread_id: str = "default"

# 변경: /internal/chat 핸들러
@app.post("/internal/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    doc_ids = req.doc_ids or []
    config = {
        "configurable": {
            "thread_id": req.thread_id,
            "doc_ids": doc_ids,
        }
    }
    last_message = await supervisor_agent.run(req.query, config=config)
    answer = last_message.content if last_message else "응답을 생성할 수 없습니다."
    sources = await _collect_sources(req.query, doc_ids)
    return ChatResponse(answer=answer, sources=sources)
```

**Step 2: 서버 기동 확인**

```bash
cd ai_server
uvicorn server:app --reload --port 8000
# Expected: INFO [server] SupervisorAgent 초기화 완료
```

**Step 3: 헬스 체크**

```bash
curl http://localhost:8000/internal/health
# Expected: {"status":"ok"}
```

**Step 4: 기존 전체 테스트 PASS 확인**

```bash
pytest eval/tests/ tests/ -v
```

**Step 5: 커밋**

```bash
git add ai_server/server.py
git commit -m "feat(server): SupervisorAgent 싱글턴으로 교체, thread_id 추가"
```

---

## Task 10: db/schema.sql — Oracle DDL

**Files:**
- Create: `db/schema.sql`

**Step 1: schema.sql 작성**

```sql
-- db/schema.sql
-- Oracle LMS DB 스키마
-- NCS 직원 관리 시스템 테이블 정의

-- ============================================================
-- 시퀀스
-- ============================================================
CREATE SEQUENCE SEQ_HISTORY_ID START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE SEQ_SUBMISSION_ID START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE SEQ_RESULT_ID START WITH 1 INCREMENT BY 1 NOCACHE;

-- ============================================================
-- TB_EMPLOYEE : 직원 기본정보
-- ============================================================
CREATE TABLE TB_EMPLOYEE (
    EMPLOYEE_ID  VARCHAR2(20)  NOT NULL,
    NAME         VARCHAR2(50)  NOT NULL,
    DEPARTMENT   VARCHAR2(100) NOT NULL,
    POSITION     VARCHAR2(50),
    JOIN_DATE    DATE          NOT NULL,
    EMAIL        VARCHAR2(100),
    CREATED_AT   DATE          DEFAULT SYSDATE NOT NULL,
    CONSTRAINT PK_EMPLOYEE     PRIMARY KEY (EMPLOYEE_ID),
    CONSTRAINT UQ_EMPLOYEE_EMAIL UNIQUE (EMAIL)
);

COMMENT ON TABLE  TB_EMPLOYEE              IS '직원 기본정보';
COMMENT ON COLUMN TB_EMPLOYEE.EMPLOYEE_ID  IS '사번';
COMMENT ON COLUMN TB_EMPLOYEE.NAME         IS '이름';
COMMENT ON COLUMN TB_EMPLOYEE.DEPARTMENT   IS '부서';
COMMENT ON COLUMN TB_EMPLOYEE.POSITION     IS '직책';
COMMENT ON COLUMN TB_EMPLOYEE.JOIN_DATE    IS '입사일';
COMMENT ON COLUMN TB_EMPLOYEE.EMAIL        IS '이메일';

-- ============================================================
-- TB_EDUCATION_HISTORY : 교육 이수 내역
-- ============================================================
CREATE TABLE TB_EDUCATION_HISTORY (
    HISTORY_ID       NUMBER        NOT NULL,
    EMPLOYEE_ID      VARCHAR2(20)  NOT NULL,
    COURSE_NAME      VARCHAR2(200) NOT NULL,
    NCS_CODE         VARCHAR2(50),
    START_DATE       DATE,
    COMPLETION_DATE  DATE,
    STATUS           VARCHAR2(20)  NOT NULL,  -- 완료/진행중/미이수
    SCORE            NUMBER(5,2),
    CREATED_AT       DATE          DEFAULT SYSDATE NOT NULL,
    CONSTRAINT PK_EDUCATION_HISTORY    PRIMARY KEY (HISTORY_ID),
    CONSTRAINT FK_EDU_EMPLOYEE         FOREIGN KEY (EMPLOYEE_ID) REFERENCES TB_EMPLOYEE(EMPLOYEE_ID),
    CONSTRAINT CK_EDU_STATUS           CHECK (STATUS IN ('완료', '진행중', '미이수'))
);

COMMENT ON TABLE  TB_EDUCATION_HISTORY             IS '교육 이수 내역';
COMMENT ON COLUMN TB_EDUCATION_HISTORY.HISTORY_ID  IS '이수 ID';
COMMENT ON COLUMN TB_EDUCATION_HISTORY.NCS_CODE    IS 'NCS 분류 코드';
COMMENT ON COLUMN TB_EDUCATION_HISTORY.STATUS      IS '완료/진행중/미이수';
COMMENT ON COLUMN TB_EDUCATION_HISTORY.SCORE       IS '이수 점수';

-- ============================================================
-- TB_ASSIGNMENT_SUBMISSION : 과제 제출
-- ============================================================
CREATE TABLE TB_ASSIGNMENT_SUBMISSION (
    SUBMISSION_ID    NUMBER        NOT NULL,
    EMPLOYEE_ID      VARCHAR2(20)  NOT NULL,
    COURSE_NAME      VARCHAR2(200) NOT NULL,
    ASSIGNMENT_NAME  VARCHAR2(200) NOT NULL,
    SUBMIT_DATE      DATE,
    STATUS           VARCHAR2(20)  NOT NULL,  -- 제출/미제출/반려
    FILE_PATH        VARCHAR2(500),
    CREATED_AT       DATE          DEFAULT SYSDATE NOT NULL,
    CONSTRAINT PK_ASSIGNMENT_SUBMISSION   PRIMARY KEY (SUBMISSION_ID),
    CONSTRAINT FK_SUBMIT_EMPLOYEE         FOREIGN KEY (EMPLOYEE_ID) REFERENCES TB_EMPLOYEE(EMPLOYEE_ID),
    CONSTRAINT CK_SUBMIT_STATUS           CHECK (STATUS IN ('제출', '미제출', '반려'))
);

COMMENT ON TABLE  TB_ASSIGNMENT_SUBMISSION                IS '과제 제출';
COMMENT ON COLUMN TB_ASSIGNMENT_SUBMISSION.SUBMISSION_ID  IS '제출 ID';
COMMENT ON COLUMN TB_ASSIGNMENT_SUBMISSION.STATUS         IS '제출/미제출/반려';
COMMENT ON COLUMN TB_ASSIGNMENT_SUBMISSION.FILE_PATH      IS '제출 파일 경로';

-- ============================================================
-- TB_GRADING_RESULT : 채점 결과
-- ============================================================
CREATE TABLE TB_GRADING_RESULT (
    RESULT_ID      NUMBER        NOT NULL,
    SUBMISSION_ID  NUMBER        NOT NULL,
    EMPLOYEE_ID    VARCHAR2(20)  NOT NULL,
    GRADER_ID      VARCHAR2(20)  NOT NULL,
    SCORE          NUMBER(5,2),
    PASS_YN        CHAR(1)       NOT NULL,  -- Y/N
    FEEDBACK       VARCHAR2(4000),
    GRADED_DATE    DATE,
    CREATED_AT     DATE          DEFAULT SYSDATE NOT NULL,
    CONSTRAINT PK_GRADING_RESULT        PRIMARY KEY (RESULT_ID),
    CONSTRAINT FK_GRADE_SUBMISSION      FOREIGN KEY (SUBMISSION_ID) REFERENCES TB_ASSIGNMENT_SUBMISSION(SUBMISSION_ID),
    CONSTRAINT FK_GRADE_EMPLOYEE        FOREIGN KEY (EMPLOYEE_ID) REFERENCES TB_EMPLOYEE(EMPLOYEE_ID),
    CONSTRAINT FK_GRADE_GRADER          FOREIGN KEY (GRADER_ID) REFERENCES TB_EMPLOYEE(EMPLOYEE_ID),
    CONSTRAINT CK_PASS_YN               CHECK (PASS_YN IN ('Y', 'N'))
);

COMMENT ON TABLE  TB_GRADING_RESULT              IS '채점 결과';
COMMENT ON COLUMN TB_GRADING_RESULT.RESULT_ID    IS '채점 ID';
COMMENT ON COLUMN TB_GRADING_RESULT.GRADER_ID    IS '채점자 사번';
COMMENT ON COLUMN TB_GRADING_RESULT.PASS_YN      IS '합격 여부 Y/N';
COMMENT ON COLUMN TB_GRADING_RESULT.FEEDBACK     IS '피드백';
```

**Step 2: 커밋**

```bash
git add db/schema.sql
git commit -m "feat(db): Oracle LMS DB 스키마 DDL 추가 (4개 테이블)"
```

---

## Task 11: db/dummy_data.sql — 더미 데이터

**Files:**
- Create: `db/dummy_data.sql`

**Step 1: dummy_data.sql 작성**

```sql
-- db/dummy_data.sql
-- Oracle LMS DB 더미 데이터
-- 테스트 및 개발 환경용

-- ============================================================
-- TB_EMPLOYEE 더미 데이터 (10명)
-- ============================================================
INSERT INTO TB_EMPLOYEE VALUES ('EMP001', '홍길동', '소프트웨어개발팀', '선임개발자', DATE '2020-03-02', 'hong@company.com', SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP002', '김철수', '소프트웨어개발팀', '주임개발자', DATE '2021-07-01', 'kim@company.com', SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP003', '이영희', 'QA팀', '선임QA', DATE '2019-01-15', 'lee@company.com', SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP004', '박민수', '데이터분석팀', '주임분석가', DATE '2022-04-11', 'park@company.com', SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP005', '최지연', '인프라팀', '클라우드엔지니어', DATE '2020-09-07', 'choi@company.com', SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP006', '정수현', '소프트웨어개발팀', '사원', DATE '2024-02-19', 'jung@company.com', SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP007', '강동원', 'QA팀', '주임QA', DATE '2021-11-03', 'kang@company.com', SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP008', '윤서연', '데이터분석팀', '선임분석가', DATE '2018-06-25', 'yoon@company.com', SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP009', '조현우', '인프라팀', '사원', DATE '2023-08-14', 'cho@company.com', SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP010', '한미래', 'HR팀', '채점관리자', DATE '2017-03-20', 'han@company.com', SYSDATE);

-- ============================================================
-- TB_EDUCATION_HISTORY 더미 데이터
-- ============================================================
-- EMP001 홍길동
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP001', 'Python 기반 소프트웨어 개발', 'SW-20-01', DATE '2023-03-01', DATE '2023-03-31', '완료', 95.0, SYSDATE);
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP001', 'Java 엔터프라이즈 개발', 'SW-20-02', DATE '2023-06-01', DATE '2023-06-30', '완료', 88.5, SYSDATE);
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP001', '클라우드 서비스 운용', 'IT-CL-01', DATE '2024-01-10', NULL, '진행중', NULL, SYSDATE);

-- EMP002 김철수
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP002', 'Python 기반 소프트웨어 개발', 'SW-20-01', DATE '2023-03-01', DATE '2023-03-31', '완료', 78.0, SYSDATE);
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP002', '데이터베이스 설계 및 구축', 'DB-15-01', DATE '2023-09-01', DATE '2023-09-30', '완료', 82.0, SYSDATE);
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP002', 'UI/UX 설계', 'UX-10-01', DATE '2024-02-01', NULL, '미이수', NULL, SYSDATE);

-- EMP003 이영희
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP003', '소프트웨어 테스트 설계', 'QA-20-01', DATE '2022-05-01', DATE '2022-05-31', '완료', 92.0, SYSDATE);
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP003', '테스트 자동화 구현', 'QA-20-02', DATE '2023-10-01', DATE '2023-10-31', '완료', 90.5, SYSDATE);

-- EMP004 박민수
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP004', '빅데이터 분석', 'DA-25-01', DATE '2023-04-01', DATE '2023-04-30', '완료', 85.0, SYSDATE);
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP004', '머신러닝 모델 개발', 'DA-25-02', DATE '2024-01-01', NULL, '진행중', NULL, SYSDATE);

-- EMP006 정수현 (신입)
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP006', 'Python 기반 소프트웨어 개발', 'SW-20-01', DATE '2024-03-01', NULL, '진행중', NULL, SYSDATE);

-- ============================================================
-- TB_ASSIGNMENT_SUBMISSION 더미 데이터
-- ============================================================
-- EMP001 홍길동 과제
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP001', 'Python 기반 소프트웨어 개발', 'REST API 설계 및 구현', DATE '2023-03-25', '제출', '/uploads/EMP001/python_api.zip', SYSDATE);
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP001', 'Java 엔터프라이즈 개발', 'Spring Boot 마이크로서비스 구축', DATE '2023-06-28', '제출', '/uploads/EMP001/spring_msa.zip', SYSDATE);

-- EMP002 김철수 과제
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP002', 'Python 기반 소프트웨어 개발', 'REST API 설계 및 구현', DATE '2023-03-29', '제출', '/uploads/EMP002/python_api.zip', SYSDATE);
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP002', 'UI/UX 설계', 'UI 프로토타입 제작', NULL, '미제출', NULL, SYSDATE);

-- EMP003 이영희 과제
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP003', '소프트웨어 테스트 설계', '테스트 케이스 시나리오 작성', DATE '2022-05-28', '제출', '/uploads/EMP003/test_case.xlsx', SYSDATE);
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP003', '테스트 자동화 구현', 'Selenium 자동화 스크립트', DATE '2023-10-29', '제출', '/uploads/EMP003/selenium_test.zip', SYSDATE);

-- EMP006 정수현 (신입, 미제출)
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP006', 'Python 기반 소프트웨어 개발', 'REST API 설계 및 구현', NULL, '미제출', NULL, SYSDATE);

-- ============================================================
-- TB_GRADING_RESULT 더미 데이터
-- ============================================================
-- EMP001 과제 채점 (채점자: EMP010 한미래)
INSERT INTO TB_GRADING_RESULT VALUES (SEQ_RESULT_ID.NEXTVAL, 1, 'EMP001', 'EMP010', 96.0, 'Y', 'REST API 설계가 우수하며 코드 품질이 높습니다. 예외 처리 로직이 특히 잘 구현되었습니다.', DATE '2023-03-30', SYSDATE);
INSERT INTO TB_GRADING_RESULT VALUES (SEQ_RESULT_ID.NEXTVAL, 2, 'EMP001', 'EMP010', 87.0, 'Y', 'MSA 구조 설계는 양호하나 서비스 간 통신 오류 처리 부분 보완 필요.', DATE '2023-06-30', SYSDATE);

-- EMP002 과제 채점
INSERT INTO TB_GRADING_RESULT VALUES (SEQ_RESULT_ID.NEXTVAL, 3, 'EMP002', 'EMP010', 72.0, 'Y', 'API 기본 기능은 구현되었으나 인증/인가 처리가 미흡합니다.', DATE '2023-03-31', SYSDATE);

-- EMP003 과제 채점
INSERT INTO TB_GRADING_RESULT VALUES (SEQ_RESULT_ID.NEXTVAL, 5, 'EMP003', 'EMP010', 93.0, 'Y', '테스트 케이스가 체계적으로 잘 작성되었습니다. 경계값 테스트 케이스 추가 권장.', DATE '2022-05-31', SYSDATE);
INSERT INTO TB_GRADING_RESULT VALUES (SEQ_RESULT_ID.NEXTVAL, 6, 'EMP003', 'EMP010', 91.0, 'Y', 'Selenium 스크립트 품질 우수. Page Object 패턴 적용이 돋보입니다.', DATE '2023-10-31', SYSDATE);

COMMIT;
```

**Step 2: 커밋**

```bash
git add db/dummy_data.sql
git commit -m "feat(db): Oracle LMS DB 더미 데이터 추가 (직원 10명, 이수/과제/채점 데이터)"
```

---

## 최종 검증

**Step 1: 전체 테스트 PASS 확인**

```bash
cd ai_server
pytest eval/tests/ tests/ -v
# Expected: 모든 테스트 PASS
```

**Step 2: 서버 기동 및 엔드포인트 확인**

```bash
uvicorn server:app --reload --port 8000

# 헬스 체크
curl http://localhost:8000/internal/health

# 채팅 테스트 (RAG only)
curl -X POST http://localhost:8000/internal/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "NCS 소프트웨어개발 직무의 능력단위는?", "thread_id": "test-1"}'

# 채팅 테스트 (SQL only)
curl -X POST http://localhost:8000/internal/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "EMP001 홍길동의 교육 이수 내역 알려줘", "thread_id": "test-2"}'
```

**Step 3: 최종 커밋**

```bash
git add .
git commit -m "feat: 멀티에이전트 시스템 완성 (Supervisor + RAG + SQL Agent)"
```
