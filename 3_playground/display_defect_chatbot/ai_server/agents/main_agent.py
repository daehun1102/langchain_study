# DEPRECATED: hypothesis_node(graph.py)로 흡수됨. 이 파일은 더 이상 사용되지 않습니다.
# display_defect_chatbot/ai_server/agents/main_agent.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ai_server.infra.vector_store import VectorStoreManager
from ai_server.agents.prompts import HYPOTHESIS_SYSTEM_PROMPT
from ai_server.config import get_settings

settings = get_settings()
_llm = ChatOpenAI(model=settings.model_name, temperature=0.3)


async def run_main_analysis(
    defect_description: str,
    company: str,
    vsm: VectorStoreManager,
) -> list[str]:
    """RAG로 과거 사례 검색 후 원인 가설 2-3개 생성"""
    docs = await vsm.similarity_search(defect_description, k=4)
    context = "\n\n".join([d.page_content for d in docs]) if docs else "관련 사례 없음"

    messages = [
        SystemMessage(content=HYPOTHESIS_SYSTEM_PROMPT),
        HumanMessage(
            content=f"[보고 회사]: {company}\n[불량 증상]: {defect_description}\n\n[과거 사례 문서]\n{context}"
        ),
    ]
    response = await _llm.ainvoke(messages)
    text = response.content.strip()

    # "가설N: ..." 패턴 파싱
    hypotheses = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("가설") and ":" in line:
            hypotheses.append(line)

    return hypotheses if hypotheses else [text]
