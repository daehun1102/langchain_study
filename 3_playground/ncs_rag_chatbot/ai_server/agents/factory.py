# ai_server/agents/factory.py
from agents.base import BaseAgent
from agents.v1.rag_agent import ChatAgent
from agents.v1.sql_agent import SqlAgent
from agents.v1.supervisor import SupervisorAgent
from tools.rag_tool import ToolBuilder
from clients.spring.v1.employee import EmployeeClientV1
from infra.vector_store import VectorStoreManager


async def create_agent(vsm: VectorStoreManager) -> BaseAgent:
    """VectorStoreManager를 받아 완전히 조립된 Agent를 반환한다."""
    rag_tools = ToolBuilder(vsm).build_tools()

    rag_agent = ChatAgent()
    rag_agent.create_agent(rag_tools)

    employee_client = EmployeeClientV1()
    sql_agent = SqlAgent(employee_client=employee_client)
    sql_agent.create_agent()

    supervisor = SupervisorAgent(rag_agent=rag_agent, sql_agent=sql_agent)
    supervisor.create_agent()
    return supervisor
