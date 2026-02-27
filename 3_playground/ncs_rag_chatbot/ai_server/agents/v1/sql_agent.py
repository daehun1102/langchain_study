"""
sql_agent.py — 직원 이력 조회 전문 에이전트
"""
import langchain.agents as _lc_agents
import langchain.chat_models as _lc_chat
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
        super().__init__()
        self.model = _lc_chat.init_chat_model(model_name or settings.model_name)
        self.checkpointer = InMemorySaver()
        self.system_prompt = SQL_SYSTEM_PROMPT
        tool_builder = SqlToolBuilder(employee_client)
        self._tools = tool_builder.build_tools()

    def create_agent(self, tools: list = None):
        self.agent = _lc_agents.create_agent(
            self.model,
            tools or self._tools,
            system_prompt=self.system_prompt,
            checkpointer=self.checkpointer,
        )
