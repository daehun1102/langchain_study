# agent.py 개선 설계 — 싱글턴 에이전트 + Multi-turn 대화

**Date:** 2026-02-23
**Scope:** `ai_server/tool.py`, `ai_server/agent.py`, `ai_server/server.py`

---

## 목표

1. `ChatAgent`를 서버 시작 시 한 번만 생성하여 재사용한다 (싱글턴 패턴).
2. `InMemorySaver` checkpointer를 통해 `thread_id`별 대화 히스토리를 유지한다 (multi-turn).
3. `doc_ids`를 요청마다 런타임 config로 전달하여 도구가 동적으로 검색 범위를 결정한다.

---

## 핵심 기술 결정

### 문제: 요청마다 다른 doc_ids vs 싱글턴 agent

`create_agent(tools=...)` 시점에 tools가 고정된다. 기존 코드는 `doc_ids`를 클로저로 캡처하여 매 요청마다 새 tool을 만들었다. 싱글턴으로 바꾸면 이 패턴이 동작하지 않는다.

### 해결책: RunnableConfig 런타임 주입

LangChain 도구는 함수 시그니처에 `config: RunnableConfig`가 있으면 런타임에 자동 주입된다. 이를 이용해 `doc_ids`를 `config["configurable"]["doc_ids"]`로 전달한다.

```python
@tool(response_format="content_and_artifact")
async def retrieve_context(query: str, config: RunnableConfig):
    doc_ids = config["configurable"].get("doc_ids", [])
    # ... 기존 검색 로직
```

---

## 변경 범위

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `ai_server/tool.py` | 수정 | `build_tools(doc_ids)` 제거, `RunnableConfig` 주입 |
| `ai_server/agent.py` | 수정 | `checkpointer` 추가, `run()` config 파라미터화 |
| `ai_server/server.py` | 수정 | lifespan에서 agent 1회 생성, `thread_id` 필드 추가 |

---

## 설계 세부

### 1. `tool.py` 변경

**제거:**
- `build_tools(doc_ids, k)` 시그니처에서 `doc_ids` 파라미터
- `_doc_ids` 클로저 변수

**추가:**
- `config: RunnableConfig` 파라미터 (LangChain 자동 주입)
- `config["configurable"].get("doc_ids", [])` 로 런타임 doc_ids 읽기

```python
from langchain_core.runnables import RunnableConfig

class ToolBuilder:
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
            ...
        return [retrieve_context]
```

### 2. `agent.py` 변경

**`__init__`:**
- `InMemorySaver` checkpointer 생성 (인스턴스 변수로 보관)

**`create_agent(tools)`:**
- `create_agent(..., checkpointer=self.checkpointer)` 추가

**`run(query)` → `run(query, config)`:**
- `config` 파라미터 추가 (thread_id + doc_ids 포함)
- `astream(..., config=config)` 로 전달

```python
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

class ChatAgent:
    def __init__(self, model_name: str = "gpt-4o-mini", system_prompt: str = None):
        self.model = init_chat_model(model_name)
        self.checkpointer = InMemorySaver()
        if system_prompt is not None:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = _build_system_prompt()

    def create_agent(self, tools: List):
        self.agent = create_agent(
            self.model,
            tools,
            system_prompt=self.system_prompt,
            checkpointer=self.checkpointer,
        )

    async def run(self, query: str, config: dict = None):
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

### 3. `server.py` 변경

**`lifespan`에서 싱글턴 생성:**
```python
tool_builder: Optional[ToolBuilder] = None
chat_agent: Optional[ChatAgent] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store_manager, tool_builder, chat_agent
    emb = EmbeddingModel().get_embeddings()
    vector_store_manager = await VectorStoreManager.create(DB_CONNECTION, emb)
    tool_builder = ToolBuilder(vector_store_manager)
    tools = tool_builder.build_tools()      # doc_ids 없이 빌드
    chat_agent = ChatAgent()
    chat_agent.create_agent(tools)
    logger.info("[server] ChatAgent 초기화 완료")
    yield
```

**`ChatRequest`에 `thread_id` 추가:**
```python
class ChatRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None
    thread_id: str = "default"
```

**`chat()` 핸들러 단순화:**
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

---

## 호출 흐름

```
POST /internal/chat {query, thread_id, doc_ids}
  → chat_agent.run(query, config={"configurable": {"thread_id": "session-1", "doc_ids": [...]}})
    → agent.astream(..., config=config, stream_mode="values")
      → InMemorySaver: thread_id별 대화 히스토리 유지
        → retrieve_context(query, config)
          → config["configurable"]["doc_ids"] 읽어 검색 수행
```

---

## 정책 결정 사항

| 항목 | 결정 |
|------|------|
| Checkpointer 구현 | `InMemorySaver` (서버 재시작 시 초기화됨) |
| thread_id 관리 주체 | Spring Boot가 ChatRequest에 포함하여 전달 |
| doc_ids 전달 방식 | `config["configurable"]["doc_ids"]` 런타임 주입 |
| ChatAgent 수명 | 서버 프로세스와 동일 (lifespan에서 생성) |
