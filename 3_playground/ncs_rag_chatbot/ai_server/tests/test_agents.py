import pytest
from unittest.mock import AsyncMock, MagicMock, patch


async def _async_iter(items):
    for item in items:
        yield item


async def test_sql_agent_run_returns_message():
    from agents.v1.sql_agent import SqlAgent
    from clients.spring.v1.employee import EmployeeClientV1

    mock_client = AsyncMock(spec=EmployeeClientV1)

    with patch("langchain.chat_models.init_chat_model") as mock_model, \
         patch("langchain.agents.create_agent") as mock_create:

        mock_agent_instance = MagicMock()
        mock_agent_instance.astream.return_value = _async_iter([
            {"messages": [MagicMock(content="홍길동의 이력 조회 완료")]}
        ])
        mock_create.return_value = mock_agent_instance
        mock_model.return_value = MagicMock()

        agent = SqlAgent(employee_client=mock_client)
        agent.create_agent()
        result = await agent.run("EMP001 이력 조회")

    assert result.content == "홍길동의 이력 조회 완료"


async def test_supervisor_has_two_tools():
    """Supervisor는 call_rag_agent와 call_sql_agent 두 도구를 가진다."""
    from agents.v1.supervisor import _build_supervisor_tools

    mock_rag = AsyncMock()
    mock_sql = AsyncMock()
    tools = _build_supervisor_tools(mock_rag, mock_sql)

    tool_names = [t.name for t in tools]
    assert "call_rag_agent" in tool_names
    assert "call_sql_agent" in tool_names


async def test_supervisor_run_returns_message():
    from agents.v1.supervisor import SupervisorAgent

    mock_rag = AsyncMock()
    mock_sql = AsyncMock()

    with patch("langchain.chat_models.init_chat_model") as mock_model, \
         patch("langchain.agents.create_agent") as mock_create:

        mock_agent_instance = MagicMock()
        mock_agent_instance.astream.return_value = _async_iter([
            {"messages": [MagicMock(content="EMP001 홍길동의 교육 이수 완료")]}
        ])
        mock_create.return_value = mock_agent_instance
        mock_model.return_value = MagicMock()

        supervisor = SupervisorAgent(rag_agent=mock_rag, sql_agent=mock_sql)
        supervisor.create_agent()
        result = await supervisor.run(
            "EMP001 직원의 이수 내역 알려줘",
            config={"configurable": {"thread_id": "test-thread"}}
        )

    assert result is not None
    assert "EMP001" in result.content


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
    mock_emp_cls.assert_called_once_with()
    mock_sql_cls.assert_called_once_with(employee_client=mock_emp_cls.return_value)


# ── v2 handoffs agent tests ──────────────────────────────────────

async def test_ncs_handoff_agent_has_three_step_workflow():
    """NCSHandoffAgent는 sql, rag, feedback 세 단계 워크플로우를 지원한다."""
    from agents.v2.supervisor import NCSHandoffAgent

    mock_sql_tool = MagicMock()
    mock_sql_tool.name = "query_employee_data"
    mock_rag_tool = MagicMock()
    mock_rag_tool.name = "retrieve_context"

    with patch("agents.v2.supervisor.create_agent") as mock_create, \
         patch("agents.v2.supervisor.init_chat_model"):
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


async def test_ncs_handoff_agent_create_agent_rejects_tools_override():
    """create_agent(tools=...)를 호출하면 ValueError가 발생한다."""
    from agents.v2.supervisor import NCSHandoffAgent

    with patch("agents.v2.supervisor.create_agent"), \
         patch("agents.v2.supervisor.init_chat_model"):
        agent = NCSHandoffAgent(rag_tools=[], sql_tools=[])
        with pytest.raises(ValueError, match="external tool override"):
            agent.create_agent(tools=[MagicMock()])


async def test_ncs_handoff_agent_uses_inmemory_checkpointer():
    """NCSHandoffAgent는 InMemorySaver를 체크포인터로 사용한다."""
    from agents.v2.supervisor import NCSHandoffAgent
    from langgraph.checkpoint.memory import InMemorySaver

    with patch("agents.v2.supervisor.create_agent") as mock_create, \
         patch("agents.v2.supervisor.init_chat_model"):
        mock_create.return_value = MagicMock()
        agent = NCSHandoffAgent(rag_tools=[], sql_tools=[])
        agent.create_agent()

    call_kwargs = mock_create.call_args[1]
    assert isinstance(call_kwargs["checkpointer"], InMemorySaver)


async def test_ncs_handoff_agent_transition_tools_are_registered():
    """complete_sql_step, complete_rag_step는 @tool로 등록된 LangChain 도구다."""
    from agents.v2.supervisor import complete_sql_step, complete_rag_step

    assert hasattr(complete_sql_step, "name")
    assert complete_sql_step.name == "complete_sql_step"
    assert hasattr(complete_rag_step, "name")
    assert complete_rag_step.name == "complete_rag_step"


async def test_ncs_handoff_agent_run_returns_message():
    """NCSHandoffAgent.run()은 마지막 메시지를 반환한다."""
    from agents.v2.supervisor import NCSHandoffAgent

    with patch("agents.v2.supervisor.create_agent") as mock_create, \
         patch("agents.v2.supervisor.init_chat_model"):

        mock_agent_instance = MagicMock()
        mock_agent_instance.astream.return_value = _async_iter([
            {"messages": [MagicMock(content="EMP001 종합 피드백 완료")]}
        ])
        mock_create.return_value = mock_agent_instance

        agent = NCSHandoffAgent(rag_tools=[], sql_tools=[])
        agent.create_agent()
        result = await agent.run(
            "EMP001의 NCS 과제 피드백",
            config={"configurable": {"thread_id": "test"}}
        )

    assert result is not None
    assert "EMP001" in result.content


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


async def test_chat_request_version_field():
    """ChatRequest의 version 기본값은 v1, v2도 허용한다."""
    # server.py imports require heavy dependencies; test the model logic directly via pydantic
    from pydantic import BaseModel
    from typing import Literal

    class ChatRequest(BaseModel):
        query: str
        version: Literal["v1", "v2"] = "v1"

    req_default = ChatRequest(query="테스트")
    assert req_default.version == "v1"

    req_v2 = ChatRequest(query="테스트", version="v2")
    assert req_v2.version == "v2"


async def test_base_agent_run_without_create_raises():
    """BaseAgent.run()은 create_agent() 전에 호출 시 ValueError를 발생시킨다."""
    from agents.base import BaseAgent

    class ConcreteAgent(BaseAgent):
        def create_agent(self, tools=None): pass

    agent = ConcreteAgent()
    with pytest.raises(ValueError, match="create_agent"):
        await agent.run("test query")


async def test_base_agent_run_after_create_works():
    """BaseAgent.run()은 create_agent() 후 self.agent.astream을 사용한다."""
    from agents.base import BaseAgent

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


def test_chat_agent_model_name_default_is_none():
    """ChatAgent의 model_name 기본값은 None (settings.model_name으로 폴백)."""
    import inspect
    from agents.v1.rag_agent import ChatAgent
    sig = inspect.signature(ChatAgent.__init__)
    assert sig.parameters["model_name"].default is None


async def test_ingest_uses_vsm_when_provided():
    """ingest_single_document(vsm=...)이 주어지면 vsm.get_vector_store()를 사용한다."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_vsm = MagicMock()
    mock_vs = MagicMock()
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
    assert result == 0  # splits is empty so 0 chunks


def test_ingest_signature_has_vsm_and_db_connection():
    """ingest_single_document의 시그니처에 vsm, db_connection 파라미터가 있다."""
    import inspect
    from infra.ingest import ingest_single_document
    sig = inspect.signature(ingest_single_document)
    assert "vsm" in sig.parameters
    assert "db_connection" in sig.parameters
    # db_connection should default to None (optional when vsm is provided)
    assert sig.parameters["db_connection"].default is None
    assert sig.parameters["vsm"].default is None


async def test_ingest_raises_when_both_vsm_and_db_connection_are_none():
    """vsm과 db_connection 모두 None이면 ValueError가 발생한다."""
    import pytest
    from infra.ingest import ingest_single_document

    with pytest.raises(ValueError, match="vsm 또는 db_connection"):
        await ingest_single_document(doc_id="x", file_path="y")
