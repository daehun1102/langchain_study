from langchain.tools import tool
from langchain_core.tools import Tool
from typing import List

class ToolBuilder:
    """에이전트가 사용할 도구를 생성하는 클래스"""

    def __init__(self, vector_store):
        self.vector_store = vector_store

    def build_tools(self) -> List[Tool]:
        """검색 도구(retrieve_context)를 생성하여 리스트로 반환합니다."""
        
        # vector_store 객체를 클로저로 캡처하여 도구 함수 내부에서 사용
        store = self.vector_store

        @tool(response_format="content_and_artifact")
        async def retrieve_context(query: str):
            """Retrieve information to help answer a query."""
            # Async similarity search
            retrieved_docs = await store.asimilarity_search(query, k=2)
            serialized = "\n\n".join(
                (f"Source: {doc.metadata}\nContent: {doc.page_content}")
                for doc in retrieved_docs
            )
            return serialized, retrieved_docs

        return [retrieve_context]
