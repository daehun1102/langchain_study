# display_defect_chatbot/ai_server/agents/main_agent.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ai_server.infra.vector_store import VectorStoreManager
from ai_server.config import get_settings

settings = get_settings()

HYPOTHESIS_SYSTEM_PROMPT = """당신은 삼성 디스플레이 제조 공정 전문가입니다.
사용자가 보고한 픽셀 불량 증상과 과거 사례 문서를 바탕으로
원인 가설을 정확히 2-3개 제시하세요.

응답 형식 (반드시 준수):
가설1: [원인명] — [간단한 설명]
가설2: [원인명] — [간단한 설명]
가설3: [원인명] — [간단한 설명] (선택)

각 가설은 한 줄로 간결하게 작성하세요."""


async def run_main_analysis(
    defect_description: str,
    company: str,
    vsm: VectorStoreManager,
) -> list[str]:
    """RAG로 과거 사례 검색 후 원인 가설 2-3개 생성"""
    docs = await vsm.similarity_search(defect_description, k=4)
    context = "\n\n".join([d.page_content for d in docs]) if docs else "관련 사례 없음"

    llm = ChatOpenAI(model=settings.model_name, temperature=0.3)
    messages = [
        SystemMessage(content=HYPOTHESIS_SYSTEM_PROMPT),
        HumanMessage(
            content=f"[보고 회사]: {company}\n[불량 증상]: {defect_description}\n\n[과거 사례 문서]\n{context}"
        ),
    ]
    response = await llm.ainvoke(messages)
    text = response.content.strip()

    # "가설N: ..." 패턴 파싱
    hypotheses = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("가설") and ":" in line:
            hypotheses.append(line)

    return hypotheses if hypotheses else [text]
