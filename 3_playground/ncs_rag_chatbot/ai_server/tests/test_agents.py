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
    """sql 단계는 handoff_to_rag 도구를 STEP_CONFIG에 포함한다.

    Note: STEP_CONFIG["sql"]["tools"]는 create_agent() 호출 후에 채워지므로
    NCSHandoffAgent를 인스턴스화하고 create_agent()를 호출한 후 확인한다.
    """
    from agents.v2.supervisor import NCSHandoffAgent, STEP_CONFIG

    with patch("langchain.agents.create_agent"), \
         patch("langchain.chat_models.init_chat_model"):
        agent = NCSHandoffAgent(rag_tools=[], sql_tools=[])
        agent.create_agent()

    tool_names = [t.name for t in STEP_CONFIG["sql"]["tools"]]
    assert "handoff_to_rag" in tool_names


async def test_ncs_handoff_agent_rag_step_has_handoff_to_feedback_tool():
    """rag 단계는 handoff_to_feedback 도구를 STEP_CONFIG에 포함한다."""
    from agents.v2.supervisor import NCSHandoffAgent, STEP_CONFIG

    with patch("langchain.agents.create_agent"), \
         patch("langchain.chat_models.init_chat_model"):
        agent = NCSHandoffAgent(rag_tools=[], sql_tools=[])
        agent.create_agent()

    tool_names = [t.name for t in STEP_CONFIG["rag"]["tools"]]
    assert "handoff_to_feedback" in tool_names


async def test_ncs_handoff_agent_feedback_step_has_no_tools():
    """feedback 단계는 도구가 없다."""
    from agents.v2.supervisor import NCSHandoffAgent, STEP_CONFIG

    with patch("langchain.agents.create_agent"), \
         patch("langchain.chat_models.init_chat_model"):
        agent = NCSHandoffAgent(rag_tools=[], sql_tools=[])
        agent.create_agent()

    assert STEP_CONFIG["feedback"]["tools"] == []


async def test_ncs_handoff_agent_run_returns_message():
    """NCSHandoffAgent.run()은 마지막 메시지를 반환한다."""
    from agents.v2.supervisor import NCSHandoffAgent

    with patch("langchain.agents.create_agent") as mock_create, \
         patch("langchain.chat_models.init_chat_model"):

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
