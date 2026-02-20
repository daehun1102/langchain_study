"""
tool.py — LangChain Agent 검색 도구

변경 사항 (Phase 2):
- build_tools(doc_ids): Spring이 Oracle에서 조회한 doc_ids를 받아
  해당 문서 범위 내에서만 벡터 검색 수행

변경 사항 (eval Task 3):
- build_tools(doc_ids, k): k 파라미터 추가로 검색 결과 수 조절 가능
"""

from langchain.tools import tool
from langchain_core.tools import Tool
from typing import List, Optional


class ToolBuilder:

    def __init__(self, vector_store_manager):
        self.vsm = vector_store_manager

    def build_tools(self, doc_ids: Optional[List[str]] = None, k: int = 4) -> List[Tool]:
        """검색 도구를 생성한다.

        doc_ids가 주어지면 해당 문서 내에서만 검색,
        없으면 전체 벡터에서 검색한다.
        k: 검색 결과 수 (기본값 4)
        """
        vsm = self.vsm
        _doc_ids = doc_ids or []
        _k = k  # 클로저 캡처용 — 내부 함수가 파라미터 k를 직접 참조하도록 명시

        @tool(response_format="content_and_artifact")
        async def retrieve_context(query: str):
            """NCS 문서에서 질의와 관련된 내용을 검색한다.

            Spring에서 전달된 doc_ids 범위 내에서만 검색한다.
            doc_ids가 없으면 전체 문서에서 검색한다.
            """
            retrieved_docs = await vsm.similarity_search_by_doc_ids(
                query, doc_ids=_doc_ids, k=_k
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
