# agent.py 개선 구현 계획 — 싱글턴 에이전트 + Multi-turn

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `ChatAgent`를 서버 시작 시 1회 생성하고 `InMemorySaver` checkpointer로 thread_id별 multi-turn 대화를 지원한다.

**Architecture:** `tool.py`에서 `doc_ids`를 클로저 대신 `RunnableConfig`로 런타임 주입한다. `ChatAgent`에 `checkpointer`를 추가하고 `run()`이 `config` dict를 받는다. `server.py` `lifespan`에서 agent를 한 번만 생성한다.

**Tech Stack:** `langchain==1.2.9`, `langgraph==1.0.8`, `langgraph-checkpoint` (`InMemorySaver`), `langchain-core` (`RunnableConfig`), `fastapi`, `pytest`, `unittest.mock`

---

## 사전 준비: 테스트 디렉토리 생성

```bash
# ai_server/ 디렉토리에서 실행
mkdir -p tests
touch tests/__init__.py
touch tests/conftest.py
```

`ai_server/tests/conftest.py` 내용:

```python
import sys
import os
from unittest.mock import MagicMock

# ai_server/ 를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 외부 의존성 mock (테스트 환경에 설치 안 됐을 수 있음)
_MISSING_MODULES = [
    "redis",
    "langchain_openai",
    "langchain_postgres",
    "dotenv",
]
for _mod in _MISSING_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
```

---

## Task 1: `tool.py` — doc_ids 클로저 제거, RunnableConfig 런타임 주입

**Files:**
- Modify: `ai_server/tool.py`
- Create: `ai_server/tests/test_tool.py`

### Step 1: 실패하는 테스트 작성

`ai_server/tests/test_tool.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock


def make_vsm(docs=None):
    """vector_store_manager mock 헬퍼."""
    vsm = MagicMock()
    vsm.similarity_search_by_doc_ids = AsyncMock(return_value=docs or [])
    return vsm


def test_build_tools_returns_one_tool():
    """build_tools()가 tool 목록 1개를 반환해야 한다."""
    from tool import ToolBuilder
    tb = ToolBuilder(make_vsm())
    tools = tb.build_tools()
    assert len(tools) == 1


@pytest.mark.asyncio
async def test_retrieve_context_reads_doc_ids_from_config():
    """retrieve_context 도구가 config["configurable"]["doc_ids"]를 읽어야 한다."""
    from langchain_core.runnables import RunnableConfig
    from tool import ToolBuilder

    vsm = make_vsm()
    tb = ToolBuilder(vsm)
    tools = tb.build_tools()
    retrieve_context = tools[0]

    config: RunnableConfig = {"configurable": {"doc_ids": ["doc-1", "doc-2"]}}
    await retrieve_context.ainvoke({"query": "테스트 질의"}, config=config)

    vsm.similarity_search_by_doc_ids.assert_called_once_with(
        "테스트 질의", doc_ids=["doc-1", "doc-2"], k=4
    )


@pytest.mark.asyncio
async def test_retrieve_context_defaults_to_empty_doc_ids():
    """config에 doc_ids가 없으면 빈 리스트로 검색해야 한다."""
    from langchain_core.runnables import RunnableConfig
    from tool import ToolBuilder

    vsm = make_vsm()
    tb = ToolBuilder(vsm)
    tools = tb.build_tools()
    retrieve_context = tools[0]

    config: RunnableConfig = {"configurable": {}}
    await retrieve_context.ainvoke({"query": "테스트"}, config=config)

    vsm.similarity_search_by_doc_ids.assert_called_once_with(
        "테스트", doc_ids=[], k=4
    )
```

### Step 2: 테스트 실행하여 실패 확인

```bash
cd ai_server
pytest tests/test_tool.py -v
```

예상 결과: `FAILED` — `build_tools()` 시그니처 불일치 또는 config 주입 없음

### Step 3: `tool.py` 구현

`ai_server/tool.py` 전체를 아래로 교체:

```python
"""
tool.py — LangChain Agent 검색 도구

변경 사항 (Phase 4):
- build_tools(doc_ids, k) → build_tools(k): doc_ids 파라미터 제거
- retrieve_context: config: RunnableConfig로 doc_ids 런타임 주입
  (Spring이 config["configurable"]["doc_ids"]로 전달)
"""

from langchain.tools import tool
from langchain_core.tools import Tool
from langchain_core.runnables import RunnableConfig
from typing import List, Optional


class ToolBuilder:

    def __init__(self, vector_store_manager):
        self.vsm = vector_store_manager

    def build_tools(self, k: int = 4) -> List[Tool]:
        """검색 도구를 생성한다.

        doc_ids는 런타임에 config["configurable"]["doc_ids"]로 전달된다.
        k: 검색 결과 수 (기본값 4)
        """
        vsm = self.vsm
        _k = k

        @tool(response_format="content_and_artifact")
        async def retrieve_context(query: str, config: RunnableConfig):
            """NCS 문서에서 질의와 관련된 내용을 검색한다.

            config["configurable"]["doc_ids"] 범위 내에서만 검색한다.
            doc_ids가 없으면 전체 문서에서 검색한다.
            """
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

### Step 4: 테스트 통과 확인

```bash
cd ai_server
pytest tests/test_tool.py -v
```

예상 결과: 모든 테스트 `PASSED`

### Step 5: 커밋

```bash
git add ai_server/tool.py ai_server/tests/__init__.py ai_server/tests/conftest.py ai_server/tests/test_tool.py
git commit -m "feat(tool): doc_ids 클로저 제거, RunnableConfig 런타임 주입으로 전환"
```

---

## Task 2: `agent.py` — checkpointer 추가, run()에 config 파라미터화

**Files:**
- Modify: `ai_server/agent.py`
- Create: `ai_server/tests/test_agent.py`

### Step 1: 실패하는 테스트 작성

`ai_server/tests/test_agent.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_mock_agent():
    """astream을 모킹하는 agent 헬퍼."""
    mock_agent = MagicMock()
    ai_message = MagicMock()
    ai_message.content = "테스트 응답"
    mock_agent.astream = AsyncMock(return_value=aiter([{"messages": [ai_message]}]))
    return mock_agent


async def aiter(items):
    for item in items:
        yield item


@patch("agent.init_chat_model", return_value=MagicMock())
@patch("agent._build_system_prompt", return_value="system prompt")
def test_chat_agent_has_checkpointer(mock_prompt, mock_model):
    """ChatAgent 초기화 후 checkpointer 속성이 있어야 한다."""
    from agent import ChatAgent
    from langgraph.checkpoint.memory import InMemorySaver
    agent = ChatAgent()
    assert hasattr(agent, "checkpointer")
    assert isinstance(agent.checkpointer, InMemorySaver)


@patch("agent.init_chat_model", return_value=MagicMock())
@patch("agent._build_system_prompt", return_value="system prompt")
@patch("agent.create_agent")
def test_create_agent_passes_checkpointer(mock_create, mock_prompt, mock_model):
    """create_agent()가 checkpointer를 인자로 전달해야 한다."""
    from agent import ChatAgent
    mock_create.return_value = MagicMock()
    a = ChatAgent()
    a.create_agent(tools=[])
    call_kwargs = mock_create.call_args.kwargs
    assert "checkpointer" in call_kwargs
    assert call_kwargs["checkpointer"] is a.checkpointer


@pytest.mark.asyncio
@patch("agent.init_chat_model", return_value=MagicMock())
@patch("agent._build_system_prompt", return_value="system prompt")
@patch("agent.create_agent")
async def test_run_raises_without_create_agent(mock_create, mock_prompt, mock_model):
    """create_agent() 호출 전에 run()하면 ValueError가 발생해야 한다."""
    from agent import ChatAgent
    a = ChatAgent()
    with pytest.raises(ValueError, match="create_agent"):
        await a.run("질의")


@pytest.mark.asyncio
@patch("agent.init_chat_model", return_value=MagicMock())
@patch("agent._build_system_prompt", return_value="system prompt")
@patch("agent.create_agent")
async def test_run_passes_config_to_astream(mock_create, mock_prompt, mock_model):
    """run()이 config를 astream()에 전달해야 한다."""
    from agent import ChatAgent
    ai_message = MagicMock()
    ai_message.content = "응답"

    mock_inner_agent = MagicMock()
    mock_inner_agent.astream = AsyncMock(
        return_value=aiter([{"messages": [ai_message]}])
    )
    mock_create.return_value = mock_inner_agent

    a = ChatAgent()
    a.create_agent(tools=[])

    config = {"configurable": {"thread_id": "t-1", "doc_ids": ["doc-1"]}}
    result = await a.run("질의", config=config)

    call_kwargs = mock_inner_agent.astream.call_args.kwargs
    assert call_kwargs["config"] == config
    assert result.content == "응답"
```

### Step 2: 테스트 실행하여 실패 확인

```bash
cd ai_server
pytest tests/test_agent.py -v
```

예상 결과: `FAILED` — `checkpointer` 속성 없음, `run()` config 파라미터 없음

### Step 3: `agent.py` 구현

`ai_server/agent.py` 전체를 아래로 교체:

```python
"""
agent.py — LangChain/LangGraph 기반 채팅 에이전트

Phase 4 변경:
- InMemorySaver checkpointer 추가 (thread_id별 multi-turn 대화 지원)
- run(query, config): config로 thread_id + doc_ids 전달받음
- ChatAgent 싱글턴 사용 (서버 시작 시 1회 생성)
"""

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from prompt_loader import get_prompt
from typing import List


PROMPT_KEYS = [
    "agent_system_prompt",
    "answer_format_prompt",
    "no_document_prompt",
    "query_enhance_prompt",
    "category_hint_prompt",
]


def _build_system_prompt() -> str:
    """Redis에서 5개 프롬프트를 로드하여 하나의 system prompt로 결합한다."""
    parts = [p for k in PROMPT_KEYS if (p := get_prompt(k))]
    return "\n\n".join(parts)


class ChatAgent:

    def __init__(self, model_name: str = "gpt-4o-mini", system_prompt: str = None):
        self.model = init_chat_model(model_name)
        self.checkpointer = InMemorySaver()
        if system_prompt is not None:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = _build_system_prompt()

    def create_agent(self, tools: List):
        """모델, 도구, checkpointer를 결합하여 에이전트를 생성한다."""
        self.agent = create_agent(
            self.model,
            tools,
            system_prompt=self.system_prompt,
            checkpointer=self.checkpointer,
        )

    async def run(self, query: str, config: dict = None):
        """사용자 질의를 처리하고 마지막 메시지를 반환한다.

        config: {"configurable": {"thread_id": "...", "doc_ids": [...]}}
        """
        if not hasattr(self, "agent"):
            raise ValueError("Agent가 생성되지 않았습니다. create_agent()를 먼저 호출하세요.")

        last_message = None
        async for event in self.agent.astream(
            {"messages": [{"role": "user", "content": query}]},
            config=config or {},
            stream_mode="values",
        ):
            last_message = event["messages"][-1]

        return last_message
```

### Step 4: 테스트 통과 확인

```bash
cd ai_server
pytest tests/test_agent.py -v
```

예상 결과: 모든 테스트 `PASSED`

### Step 5: 커밋

```bash
git add ai_server/agent.py ai_server/tests/test_agent.py
git commit -m "feat(agent): InMemorySaver checkpointer 추가, run()에 config 파라미터 추가"
```

---

## Task 3: `server.py` — 싱글턴 agent, thread_id 필드 추가

**Files:**
- Modify: `ai_server/server.py`
- Create: `ai_server/tests/test_server.py`

### Step 1: 실패하는 테스트 작성

`ai_server/tests/test_server.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_lifespan_deps():
    """lifespan 외부 의존성을 모킹한다."""
    with patch("server.EmbeddingModel") as mock_emb, \
         patch("server.VectorStoreManager") as mock_vsm, \
         patch("server.ToolBuilder") as mock_tb, \
         patch("server.ChatAgent") as mock_agent_cls, \
         patch("server.setup_tracing"):

        mock_vsm.create = AsyncMock(return_value=MagicMock())
        mock_tb.return_value.build_tools.return_value = []
        mock_agent_instance = MagicMock()
        mock_agent_cls.return_value = mock_agent_instance

        yield {
            "agent_cls": mock_agent_cls,
            "agent_instance": mock_agent_instance,
        }


def test_chat_request_has_thread_id_field():
    """ChatRequest 모델에 thread_id 필드가 있어야 한다."""
    import importlib
    import sys
    # server 모듈을 직접 import하지 않고 모델만 확인
    # (lifespan 의존성 우회)
    with patch("server.setup_tracing"), \
         patch("server.load_dotenv"):
        from server import ChatRequest
        req = ChatRequest(query="테스트", thread_id="session-1")
        assert req.thread_id == "session-1"


def test_chat_request_thread_id_defaults_to_default():
    """ChatRequest의 thread_id 기본값은 'default'여야 한다."""
    with patch("server.setup_tracing"), \
         patch("server.load_dotenv"):
        from server import ChatRequest
        req = ChatRequest(query="테스트")
        assert req.thread_id == "default"
```

### Step 2: 테스트 실행하여 실패 확인

```bash
cd ai_server
pytest tests/test_server.py -v
```

예상 결과: `FAILED` — `ChatRequest`에 `thread_id` 필드 없음

### Step 3: `server.py` 수정

**변경 1: global 변수 추가 (line 45 근처)**

`vector_store_manager: Optional[VectorStoreManager] = None` 아래에 추가:

```python
tool_builder: Optional[ToolBuilder] = None
chat_agent: Optional[ChatAgent] = None
```

**변경 2: import 추가**

파일 상단 import 블록에서 `ToolBuilder` 이미 있으므로 추가 불필요. `ChatAgent` import 확인:
- `from agent import ChatAgent` ✓ (이미 있음)
- `from tool import ToolBuilder` ✓ (이미 있음)

**변경 3: `lifespan` 함수 수정**

기존:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store_manager
    emb = EmbeddingModel().get_embeddings()
    vector_store_manager = await VectorStoreManager.create(DB_CONNECTION, emb)
    logger.info("[server] VectorStoreManager 초기화 완료")
    yield
```

교체:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store_manager, tool_builder, chat_agent
    emb = EmbeddingModel().get_embeddings()
    vector_store_manager = await VectorStoreManager.create(DB_CONNECTION, emb)
    logger.info("[server] VectorStoreManager 초기화 완료")

    tool_builder = ToolBuilder(vector_store_manager)
    tools = tool_builder.build_tools()
    chat_agent = ChatAgent()
    chat_agent.create_agent(tools)
    logger.info("[server] ChatAgent 초기화 완료")
    yield
```

**변경 4: `ChatRequest` 모델에 thread_id 추가**

기존:
```python
class ChatRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None
```

교체:
```python
class ChatRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None
    thread_id: str = "default"
```

**변경 5: `chat()` 핸들러 단순화**

기존:
```python
@app.post("/internal/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    doc_ids = req.doc_ids or []

    tool_builder = ToolBuilder(vector_store_manager)
    tools = tool_builder.build_tools(doc_ids=doc_ids)

    agent = ChatAgent()
    agent.create_agent(tools)

    last_message = await agent.run(req.query)
    answer = last_message.content if last_message else "응답을 생성할 수 없습니다."

    sources = await _collect_sources(req.query, doc_ids)

    return ChatResponse(answer=answer, sources=sources)
```

교체:
```python
@app.post("/internal/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    doc_ids = req.doc_ids or []
    config = {
        "configurable": {
            "thread_id": req.thread_id,
            "doc_ids": doc_ids,
        }
    }

    last_message = await chat_agent.run(req.query, config=config)
    answer = last_message.content if last_message else "응답을 생성할 수 없습니다."

    sources = await _collect_sources(req.query, doc_ids)

    return ChatResponse(answer=answer, sources=sources)
```

### Step 4: 테스트 통과 확인

```bash
cd ai_server
pytest tests/test_server.py -v
```

예상 결과: 모든 테스트 `PASSED`

### Step 5: 전체 테스트 실행

```bash
cd ai_server
pytest tests/ -v
```

예상 결과: 모든 테스트 `PASSED`

### Step 6: 커밋

```bash
git add ai_server/server.py ai_server/tests/test_server.py
git commit -m "feat(server): ChatAgent 싱글턴 생성, ChatRequest에 thread_id 추가"
```

---

## 최종 검증

### 수동 테스트 (서버 기동 후)

```bash
# 서버 시작
cd ai_server
uvicorn server:app --reload --port 8000

# 헬스 체크
curl http://localhost:8000/internal/health

# 첫 번째 턴 (새 세션)
curl -X POST http://localhost:8000/internal/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "NCS란 무엇인가요?", "thread_id": "session-abc"}'

# 두 번째 턴 (같은 세션 — 이전 대화 유지)
curl -X POST http://localhost:8000/internal/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "방금 설명한 내용을 요약해줘", "thread_id": "session-abc"}'
```

두 번째 요청에서 이전 대화 컨텍스트를 바탕으로 응답하면 multi-turn 동작 확인 완료.

---

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| `ai_server/tool.py` | `build_tools(doc_ids)` → `build_tools()`, `RunnableConfig` 주입 |
| `ai_server/agent.py` | `InMemorySaver` checkpointer, `run(config=)` |
| `ai_server/server.py` | 싱글턴 lifespan, `thread_id` 필드, 핸들러 단순화 |
| `ai_server/tests/conftest.py` | 새 파일 — sys.path + mock 설정 |
| `ai_server/tests/test_tool.py` | 새 파일 — tool 단위 테스트 |
| `ai_server/tests/test_agent.py` | 새 파일 — agent 단위 테스트 |
| `ai_server/tests/test_server.py` | 새 파일 — server 모델 테스트 |
