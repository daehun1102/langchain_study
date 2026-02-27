"""
supervisor.py — NCS 관리 감독관 Supervisor Agent

RAG Agent와 SQL Agent를 @tool로 래핑하여 LLM 기반 라우팅을 수행한다.
순차 처리 원칙: SQL 조회가 필요하면 먼저 실행 후, 결과를 컨텍스트에 포함해 RAG 호출.
"""
import langchain.agents as _lc_agents
import langchain.chat_models as _lc_chat
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from agents.base import BaseAgent
from config import settings
from typing import List

SUPERVISOR_SYSTEM_PROMPT = (
    "너는 NCS(국가직무능력표준) 직원 관리 감독관 AI야.\n\n"
    "## 도구 사용 규칙\n"
    "1. 직원 조회 단계 (SQL)\n"
    "   - 질문에 사번(예: EMP001) 또는 직원 이름이 포함되어 있으면 가장 먼저 `call_sql_agent`를 호출해.\n"
    "   - 조회가 완료되면 결과를 보고 직원이 작성한 과제 내용을 사용자에게 마크다운 형식으로 보여줘.\n"
    "2. NCS 검색 단계 (RAG)\n"
    "   - NCS 항목이나 키워드로 `call_rag_agent`를 호출해서 관련 NCS 기준 문서를 검색해.\n"
    "   - 검색 결과 중 가장 관련성이 높고 피드백에 도움이 될만한 내용을 사용자에게 마크다운 형식으로 보여줘.\n"
    "3. 종합 피드백 작성 단계\n"
    "   - 직전까지 찾아낸 직원 이력과 NCS 검색 결과를 종합하여 명확한 최종 피드백을 생성해.\n\n"
    "## 답변 원칙\n"
    "- 모든 답변은 마크다운 형식으로 작성\n"
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
        NCS 기준, 직무능력, 교육과정 내용에 관한 질문에 사용한다.
        
        Args:
            query: 검색어
            config: RunnableConfig
        
        Returns:
            검색 결과
        """
        result = await _rag.run(query, config=config)
        return result.content if result else "RAG 에이전트 응답 없음"

    @tool
    async def call_sql_agent(identifier: str, config: RunnableConfig) -> str:
        """직원의 교육 이수 내역, 과제 제출, 채점 결과를 조회하여 답변한다.
        사번 또는 직원 이름이 포함된 질문에 사용한다.
        
        Args:
            identifier: 사번 또는 직원 이름
            config: RunnableConfig
        
        Returns:
            직원 이력 정보
        """
        result = await _sql.run(identifier, config=config)
        return result.content if result else "SQL 에이전트 응답 없음"

    return [call_rag_agent, call_sql_agent]


class SupervisorAgent(BaseAgent):

    def __init__(self, rag_agent, sql_agent, model_name: str = None):
        super().__init__()
        self.model = _lc_chat.init_chat_model(model_name or settings.model_name)
        self.checkpointer = InMemorySaver()
        self.system_prompt = SUPERVISOR_SYSTEM_PROMPT
        self._tools = _build_supervisor_tools(rag_agent, sql_agent)

    def create_agent(self, tools: list = None):
        self.agent = _lc_agents.create_agent(
            self.model,
            tools or self._tools,
            system_prompt=self.system_prompt,
            checkpointer=self.checkpointer,
        )
