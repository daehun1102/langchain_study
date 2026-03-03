# display_defect_chatbot/ai_server/agents/synthesis_node.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ai_server.config import get_settings
import json

settings = get_settings()

SYNTHESIS_SYSTEM_PROMPT = """당신은 삼성 디스플레이 품질관리 전문가입니다.
공정이력, 반송이력, 테스트결과 데이터를 종합하여 구체적인 조치 방안을 제시하세요.

응답 구조:
## 원인 분석 요약
(선택된 가설 + 수집 데이터 기반 분석)

## 즉시 조치 사항
1. ...
2. ...

## 재발 방지 대책
1. ...
2. ...

## 추가 확인 필요 사항
- ..."""


async def synthesis_node(state: dict) -> dict:
    """서브에이전트 3종 결과를 종합하여 최종 조치안 생성"""
    llm = ChatOpenAI(model=settings.model_name, temperature=0.2)

    def fmt(data: list) -> str:
        if not data:
            return "데이터 없음"
        return json.dumps(data, ensure_ascii=False, default=str, indent=2)

    content = f"""
[선택된 가설]: {state.get('selected_hypothesis', '미선택')}
[불량 증상]: {state.get('defect_description', '')}
[회사]: {state.get('company', '')}

[공정이력 데이터]
{fmt(state.get('process_history_result', []))}

[반송이력 데이터]
{fmt(state.get('return_history_result', []))}

[테스트결과 데이터]
{fmt(state.get('test_result', []))}
"""
    messages = [
        SystemMessage(content=SYNTHESIS_SYSTEM_PROMPT),
        HumanMessage(content=content),
    ]
    response = await llm.ainvoke(messages)
    return {"final_action_plan": response.content}
