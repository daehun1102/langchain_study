import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ai_server.agents.state import SubAgentInput, AgentOutputSchema
from ai_server.agents.prompts import TEST_RESULT_ANALYSIS_PROMPT
from ai_server.tools.sql_tools import query_test_history
from ai_server.config import get_settings

settings = get_settings()
_structured_llm = ChatOpenAI(model=settings.model_name, temperature=0).with_structured_output(AgentOutputSchema, method="function_calling")


async def test_history_node(state: SubAgentInput) -> dict:
    """테스트이력 에이전트: 조회 + LLM 분석 → suspect_rows + analysis"""
    rows = await query_test_history(state["product_id"])

    content = f"""[선택된 가설]: {state["selected_hypothesis"]}
[불량 증상]: {state["defect_description"]}

[테스트결과 데이터]
{json.dumps(rows, ensure_ascii=False, default=str, indent=2)}"""

    messages = [
        SystemMessage(content=TEST_RESULT_ANALYSIS_PROMPT),
        HumanMessage(content=content),
    ]
    result: AgentOutputSchema = await _structured_llm.ainvoke(messages)
    return {"test_history_result": {"suspect_rows": result.suspect_rows, "analysis": result.analysis}}