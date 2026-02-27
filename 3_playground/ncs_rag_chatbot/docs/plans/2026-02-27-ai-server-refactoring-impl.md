# AI Server 리팩토링 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** ai_server Python 코드의 중복 제거, 설정 일관성 확보, ingest 커넥션 최적화

**Architecture:** 3개의 독립적 리팩토링 작업 — (1) BaseAgent에 run() 이동, (2) 설정 상수 정리, (3) ingest에 vsm 파라미터 추가. 각 작업은 기존 테스트를 깨지 않으면서 진행된다.

**Tech Stack:** Python 3.13, FastAPI, LangChain, LangGraph, pytest (asyncio_mode=auto)

**테스트 실행 디렉토리:** `ai_server/` (conftest.py가 sys.path 설정)

---

## Task 1: BaseAgent에 run() 기본 구현 이동

**Files:**
- Modify: `ai_server/agents/base.py`
- Modify: `ai_server/agents/v1/rag_agent.py`
- Modify: `ai_server/agents/v1/sql_agent.py`
- Modify: `ai_server/agents/v1/supervisor.py`
- Modify: `ai_server/agents/v2/supervisor.py`
- Test: `ai_server/tests/test_agents.py` (기존 테스트 회귀 확인)

**Step 1: 새 테스트 추가 — BaseAgent가 run()을 제공하는지 확인**

`ai_server/tests/test_agents.py` 끝에 추가:

```python
async def test_base_agent_run_without_create_raises():
    """BaseAgent.run()은 create_agent() 전에 호출 시 ValueError를 발생시킨다."""
    from agents.base import BaseAgent
    from unittest.mock import MagicMock, patch

    class ConcreteAgent(BaseAgent):
        def create_agent(self, tools=None): pass

    agent = ConcreteAgent()
    with pytest.raises(ValueError, match="create_agent"):
        await agent.run("test query")


async def test_base_agent_run_after_create_works():
    """BaseAgent.run()은 create_agent() 후 self.agent.astream을 사용한다."""
    from agents.base import BaseAgent
    from unittest.mock import MagicMock

    async def _fake_astream(*args, **kwargs):
        yield {"messages": [MagicMock(content="ok")]}

    class ConcreteAgent(BaseAgent):
        def create_agent(self, tools=None):
            self.agent = MagicMock()
            self.agent.astream = _fake_astream

    agent = ConcreteAgent()
    agent.create_agent()
    result = await agent.run("query")
    assert result.content == "ok"
```

**Step 2: 테스트 실패 확인**

```
cd ai_server
pytest tests/test_agents.py::test_base_agent_run_without_create_raises tests/test_agents.py::test_base_agent_run_after_create_works -v
```
Expected: FAIL — `BaseAgent` 인스턴스화 불가 (abstractmethod) 또는 `run()` 없음

**Step 3: BaseAgent 수정**

`ai_server/agents/base.py`를 다음으로 교체:

```python
from abc import ABC, abstractmethod


class BaseAgent(ABC):

    def __init__(self):
        self.agent = None

    @abstractmethod
    def create_agent(self, tools: list = None): ...

    async def run(self, query: str, config: dict = None):
        if self.agent is None:
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

**Step 4: 새 테스트 통과 확인**

```
pytest tests/test_agents.py::test_base_agent_run_without_create_raises tests/test_agents.py::test_base_agent_run_after_create_works -v
```
Expected: PASS

**Step 5: 자식 에이전트 4개에서 run() 삭제 + self.agent = None 추가**

`ai_server/agents/v1/rag_agent.py` 수정:
- `__init__`에 `self.agent = None` 추가 (마지막 줄)
- `run()` 메서드 전체 삭제 (14줄)

```python
class ChatAgent(BaseAgent):

    def __init__(self, model_name: str = None, system_prompt: str = None):
        super().__init__()                    # ← 추가
        self.model = init_chat_model(model_name or settings.model_name)
        self.checkpointer = InMemorySaver()
        self.system_prompt = system_prompt if system_prompt is not None else _build_system_prompt()

    def create_agent(self, tools: List = None):
        self.agent = _lc_agents.create_agent(
            self.model,
            tools,
            system_prompt=self.system_prompt,
            checkpointer=self.checkpointer,
        )
    # run() 삭제 — BaseAgent에서 상속
```

> 주의: `model_name` 기본값은 이 단계에서 Task 2까지 `None`으로 바꾼다 (Task 2에서 마저 처리).

`ai_server/agents/v1/sql_agent.py` 수정:
- `__init__`에 `super().__init__()` 추가 (첫 줄)
- `run()` 메서드 전체 삭제

```python
class SqlAgent(BaseAgent):

    def __init__(self, employee_client, model_name: str = None):
        super().__init__()                    # ← 추가
        self.model = _lc_chat.init_chat_model(model_name or settings.model_name)
        ...
    # run() 삭제
```

`ai_server/agents/v1/supervisor.py` 수정:
- `SupervisorAgent.__init__`에 `super().__init__()` 추가
- `run()` 메서드 전체 삭제

```python
class SupervisorAgent(BaseAgent):

    def __init__(self, rag_agent, sql_agent, model_name: str = None):
        super().__init__()                    # ← 추가
        ...
    # run() 삭제
```

`ai_server/agents/v2/supervisor.py` 수정:
- `NCSHandoffAgent.__init__`에 `super().__init__()` 추가
- `run()` 메서드 전체 삭제

```python
class NCSHandoffAgent(BaseAgent):

    def __init__(self, rag_tools: list, sql_tools: list, model_name: str = None):
        super().__init__()                    # ← 추가
        ...
    # run() 삭제
```

**Step 6: 전체 기존 테스트 + 신규 테스트 통과 확인**

```
pytest tests/test_agents.py -v
```
Expected: ALL PASS

**Step 7: 커밋**

```bash
git add ai_server/agents/base.py \
        ai_server/agents/v1/rag_agent.py \
        ai_server/agents/v1/sql_agent.py \
        ai_server/agents/v1/supervisor.py \
        ai_server/agents/v2/supervisor.py \
        ai_server/tests/test_agents.py
git commit -m "refactor(agents): BaseAgent에 run() 기본 구현 이동, 자식 4개 중복 제거"
```

---

## Task 2: 설정 일관성 정리

**Files:**
- Modify: `ai_server/agents/v1/rag_agent.py`
- Modify: `ai_server/config.py`
- Modify: `ai_server/infra/ingest.py`
- Test: `ai_server/tests/test_config.py` (기존 테스트 수정), `ai_server/tests/test_agents.py`

### 2-1. ChatAgent 모델명 통일

**Step 1: 테스트 작성**

`ai_server/tests/test_agents.py`에 추가:

```python
def test_chat_agent_uses_settings_model_name():
    """ChatAgent()는 settings.model_name을 기본 모델로 사용한다."""
    from unittest.mock import patch, MagicMock

    with patch("agents.v1.rag_agent.init_chat_model") as mock_init, \
         patch("agents.v1.rag_agent.settings") as mock_settings:
        mock_settings.model_name = "gpt-4o"
        mock_init.return_value = MagicMock()

        from agents.v1.rag_agent import ChatAgent
        import importlib
        import agents.v1.rag_agent as rag_mod
        importlib.reload(rag_mod)

        agent = rag_mod.ChatAgent()

    mock_init.assert_called_with("gpt-4o")
```

> 간소한 방법: `__init__` 시그니처 테스트 대신 `model_name` 기본값이 None인지 확인

```python
def test_chat_agent_model_name_default_is_none():
    """ChatAgent의 model_name 기본값은 None (settings.model_name으로 폴백)."""
    import inspect
    from agents.v1.rag_agent import ChatAgent
    sig = inspect.signature(ChatAgent.__init__)
    assert sig.parameters["model_name"].default is None
```

**Step 2: 실패 확인**

```
pytest tests/test_agents.py::test_chat_agent_model_name_default_is_none -v
```
Expected: FAIL (`default == "gpt-4o-mini"`)

**Step 3: rag_agent.py 수정**

`ai_server/agents/v1/rag_agent.py`:
- `from config import settings` import 추가
- `__init__` 시그니처 변경: `model_name: str = None`
- `self.model = init_chat_model(model_name or settings.model_name)`

```python
from config import settings  # ← 추가

class ChatAgent(BaseAgent):

    def __init__(self, model_name: str = None, system_prompt: str = None):
        super().__init__()
        self.model = init_chat_model(model_name or settings.model_name)  # ← 수정
        ...
```

**Step 4: 통과 확인**

```
pytest tests/test_agents.py::test_chat_agent_model_name_default_is_none -v
```
Expected: PASS

### 2-2. agent_version 삭제

**Step 5: test_config.py에서 agent_version 검증 없는지 확인**

```
grep -n "agent_version" ai_server/tests/test_config.py
```
Expected: 출력 없음 (기존 테스트가 agent_version을 검증하지 않음)

**Step 6: config.py에서 agent_version 삭제**

`ai_server/config.py`에서 `agent_version: str = "v1"` 줄 삭제:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_connection: str = "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db"
    spring_base_url: str = "http://localhost:8080"
    redis_host: str = "localhost"
    redis_port: int = 6379
    model_name: str = "gpt-4o-mini"
    spring_api_version: str = "v1"
    # agent_version 삭제됨
```

**Step 7: config 테스트 통과 확인**

```
pytest tests/test_config.py -v
```
Expected: PASS

### 2-3. TABLE_NAME 단일 소스화

**Step 8: 테스트 작성**

`ai_server/tests/test_config.py`에 추가:

```python
def test_ingest_uses_same_table_name_as_vector_store():
    """ingest.py와 vector_store.py는 동일한 TABLE_NAME을 사용한다."""
    from infra.vector_store import TABLE_NAME as vs_name
    from infra.ingest import TABLE_NAME as ingest_name
    assert vs_name == ingest_name
```

**Step 9: 테스트 실패 확인** (현재는 각자 정의하므로 값은 같지만 import 경로가 다름 — 이 테스트는 통과할 수도 있음. 통과한다면 Step 10 스킵 불가: ingest.py를 import 방식으로 변경해야 동일 소스임을 보장)

```
pytest tests/test_config.py::test_ingest_uses_same_table_name_as_vector_store -v
```

**Step 10: ingest.py TABLE_NAME 수정**

`ai_server/infra/ingest.py`:
- 기존 `TABLE_NAME = "ncs_vectors"` 줄 삭제
- `from infra.vector_store import TABLE_NAME` 추가

```python
from infra.vector_store import TABLE_NAME  # ← 추가 (기존 정의 대체)
```

**Step 11: 전체 config 테스트 통과 확인**

```
pytest tests/test_config.py -v
```
Expected: ALL PASS

**Step 12: 커밋**

```bash
git add ai_server/agents/v1/rag_agent.py \
        ai_server/config.py \
        ai_server/infra/ingest.py \
        ai_server/tests/test_agents.py \
        ai_server/tests/test_config.py
git commit -m "refactor(config): ChatAgent 모델명 통일, agent_version 삭제, TABLE_NAME 단일 소스화"
```

---

## Task 3: ingest_single_document vsm 파라미터 추가

**Files:**
- Modify: `ai_server/infra/ingest.py`
- Modify: `ai_server/server.py`
- Test: `ai_server/tests/test_agents.py` (새 테스트 추가)

**Step 1: 테스트 작성**

`ai_server/tests/test_agents.py`에 추가:

```python
async def test_ingest_uses_vsm_when_provided():
    """ingest_single_document(vsm=...)이 주어지면 vsm.get_vector_store()를 사용한다."""
    from unittest.mock import AsyncMock, MagicMock, patch
    import inspect

    mock_vsm = MagicMock()
    mock_vs = AsyncMock()
    mock_vsm.get_vector_store.return_value = mock_vs
    mock_vs.aadd_documents = AsyncMock(return_value=None)

    mock_loader = MagicMock()
    mock_loader.load.return_value = []
    mock_splitter = MagicMock()
    mock_splitter.split_documents.return_value = []

    with patch("infra.ingest.DocumentLoader", return_value=mock_loader), \
         patch("infra.ingest.DocumentSplitter", return_value=mock_splitter):
        from infra.ingest import ingest_single_document
        result = await ingest_single_document(
            doc_id="test-id",
            file_path="/fake/path.pdf",
            vsm=mock_vsm,
        )

    mock_vsm.get_vector_store.assert_called_once()
    assert result == 0  # splits가 비어 있으므로 0


async def test_ingest_without_vsm_requires_db_connection():
    """vsm이 없으면 db_connection을 사용한다."""
    import inspect
    from infra.ingest import ingest_single_document
    sig = inspect.signature(ingest_single_document)
    assert "vsm" in sig.parameters
    assert "db_connection" in sig.parameters
```

**Step 2: 테스트 실패 확인**

```
pytest tests/test_agents.py::test_ingest_uses_vsm_when_provided tests/test_agents.py::test_ingest_without_vsm_requires_db_connection -v
```
Expected: FAIL — `vsm` 파라미터 없음

**Step 3: ingest.py 수정**

`ai_server/infra/ingest.py`의 `ingest_single_document()` 시그니처와 본문 수정:

```python
async def ingest_single_document(
    doc_id: str,
    file_path: str,
    db_connection: str | None = None,
    vsm=None,  # VectorStoreManager | None — 서버에서 재사용 시 전달
) -> int:
    """단일 PDF를 PGVector에 적재한다.

    Args:
        doc_id: Oracle documents 테이블의 PK (UUID)
        file_path: PDF 파일 절대 경로
        db_connection: PGVector 연결 문자열 (CLI 실행 시 필수, vsm 미사용 시)
        vsm: 서버의 VectorStoreManager 인스턴스 (전달 시 재사용, CLI는 None)

    Returns:
        저장된 청크 수
    """
    if vsm is not None:
        vector_store = vsm.get_vector_store()
    else:
        if db_connection is None:
            raise ValueError("vsm 또는 db_connection 중 하나는 필수입니다.")
        embedding_model = EmbeddingModel().get_embeddings()
        pg_engine = await _get_pg_engine(db_connection)
        vector_store = await _get_vector_store(pg_engine, embedding_model)

    loader = DocumentLoader(file_path=file_path)
    docs = loader.load()

    splitter = DocumentSplitter()
    splits = splitter.split_documents(docs)

    for doc in splits:
        doc.page_content = doc.page_content.replace("\x00", "")
        doc.metadata["doc_id"] = doc_id
        doc.metadata["page"] = doc.metadata.get("page", 0)

    await vector_store.aadd_documents(splits)
    print(f"[ingest] doc_id={doc_id}, 청크={len(splits)}개 저장 완료")
    return len(splits)
```

> `__main__` 블록은 변경 없음 — `db_connection`으로 호출하므로 기존 CLI 동작 유지.

**Step 4: 테스트 통과 확인**

```
pytest tests/test_agents.py::test_ingest_uses_vsm_when_provided tests/test_agents.py::test_ingest_without_vsm_requires_db_connection -v
```
Expected: PASS

**Step 5: server.py의 ingest 핸들러 수정**

`ai_server/server.py` — `ingest()` 엔드포인트에 `vsm=vector_store_manager` 추가:

```python
@app.post("/internal/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    """Spring에서 PDF 업로드 후 호출. PGVector에 벡터 저장."""
    try:
        chunks = await ingest_single_document(
            req.doc_id,
            req.file_path,
            vsm=vector_store_manager,   # ← 추가: 서버의 VectorStoreManager 재사용
        )
        return IngestResponse(doc_id=req.doc_id, chunks=chunks, status="INDEXED")
    except Exception:
        logger.error("[ingest] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"ingest 실패: doc_id={req.doc_id}")
```

**Step 6: 전체 테스트 회귀 확인**

```
pytest tests/ -v
```
Expected: ALL PASS

**Step 7: 커밋**

```bash
git add ai_server/infra/ingest.py \
        ai_server/server.py \
        ai_server/tests/test_agents.py
git commit -m "refactor(ingest): vsm 파라미터 추가로 서버 VectorStoreManager 재사용"
```

---

## 최종 확인

**전체 테스트 실행:**
```
cd ai_server && pytest tests/ -v
```
Expected: ALL PASS, 이전 대비 테스트 수 증가 (신규 테스트 추가됨)

**변경 파일 최종 목록:**
```
ai_server/agents/base.py
ai_server/agents/v1/rag_agent.py
ai_server/agents/v1/sql_agent.py
ai_server/agents/v1/supervisor.py
ai_server/agents/v2/supervisor.py
ai_server/config.py
ai_server/infra/ingest.py
ai_server/server.py
ai_server/tests/test_agents.py
ai_server/tests/test_config.py
```
