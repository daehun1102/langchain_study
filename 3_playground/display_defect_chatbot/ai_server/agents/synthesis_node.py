# ai_server/agents/synthesis_node.py
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ai_server.agents.state import DefectAnalysisState
from ai_server.agents.prompts import FINAL_SYNTHESIS_SYSTEM_PROMPT
from ai_server.config import get_settings

settings = get_settings()
_llm = ChatOpenAI(model=settings.model_name, temperature=0.2)


def _fmt(result: dict | None) -> str:
    if not result:
        return "데이터 없음"
    return f"분석: {result.get('analysis', '')}\n의심 데이터: {json.dumps(result.get('suspect_rows', []), ensure_ascii=False, default=str, indent=2)}"


async def final_synthesis_node(state: DefectAnalysisState) -> dict:
    """3개 에이전트 + 장기이력 결과를 모두 포함한 최종 조치안 생성"""
    content = f"""
[선택된 가설]: {state["selected_hypothesis"]}
[불량 증상]: {state["defect_description"]}
[회사]: {state["company"]}

[공정이력 에이전트 분석]
{_fmt(state.get("process_history_result"))}

[반송이력 에이전트 분석]
{_fmt(state.get("return_history_result"))}

[테스트결과 에이전트 분석]
{_fmt(state.get("test_result"))}

[장기이력 분석]
{state.get("long_term_result") or "데이터 없음"}
"""
    messages = [
        SystemMessage(content=FINAL_SYNTHESIS_SYSTEM_PROMPT),
        HumanMessage(content=content),
    ]
    response = await _llm.ainvoke(messages)
    return {"final_action_plan": response.content}
