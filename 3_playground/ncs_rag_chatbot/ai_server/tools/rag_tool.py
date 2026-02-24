"""
rag_tool.py — RAG 검색 도구
(기존 tool.py에서 이동, RunnableConfig 패턴 적용)
"""
from langchain.tools import tool
from langchain_core.tools import Tool
from langchain_core.runnables import RunnableConfig
from typing import List, Optional


class ToolBuilder:

    def __init__(self, vector_store_manager):
        self.vsm = vector_store_manager

    def build_tools(self, k: int = 4) -> List[Tool]:
        vsm = self.vsm
        _k = k

        @tool(response_format="content_and_artifact")
        async def retrieve_context(query: str, config: RunnableConfig):
            """NCS 문서에서 질의와 관련된 내용을 검색한다.

            Spring에서 전달된 doc_ids 범위 내에서만 검색한다.
            doc_ids가 없으면 전체 문서에서 검색한다.
            """
            doc_ids = config["configurable"].get("doc_ids", [])
            retrieved_docs = await vsm.similarity_search_by_doc_ids(
                query, doc_ids=doc_ids, k=_k
            )

            if not retrieved_docs:
                return "관련 문서를 찾을 수 없습니다.", []

            serialized = "\n\n".join(
                f"[doc_id: {doc.metadata.get('doc_id', 'unknown')}, "
                f"page: {doc.metadata.get('page', 0)}]\n{doc.page_content}"
                for doc in retrieved_docs
            )
            return serialized, retrieved_docs

        return [retrieve_context]
