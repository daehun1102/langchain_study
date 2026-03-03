# display_defect_chatbot/ai_server/tools/rag_tool.py
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from ai_server.infra.vector_store import VectorStoreManager


def build_rag_tool(vsm: VectorStoreManager):
    @tool
    async def search_defect_knowledge(query: str, config: RunnableConfig) -> str:
        """과거 불량 사례 및 SOP 문서에서 관련 정보를 검색합니다."""
        doc_ids = config.get("configurable", {}).get("doc_ids")
        docs = await vsm.similarity_search(query, doc_ids=doc_ids, k=4)
        if not docs:
            return "관련 문서를 찾을 수 없습니다."
        return "\n\n".join([f"[{i+1}] {d.page_content}" for i, d in enumerate(docs)])

    return search_defect_knowledge
