from langchain.tools import tool
from langchain_core.tools import Tool
from typing import List, Optional

class ToolBuilder:
    """에이전트가 사용할 도구를 생성하는 클래스"""

    def __init__(self, vector_store):
        self.vector_store = vector_store

    def build_tools(self) -> List[Tool]:
        """검색 도구(retrieve_context)를 생성하여 리스트로 반환합니다."""

        # vector_store 객체를 클로저로 캡처하여 도구 함수 내부에서 사용
        store = self.vector_store

        @tool(response_format="content_and_artifact")
        async def retrieve_context(
            query: str,
            main_category: Optional[str] = None,
            sub_category: Optional[str] = None,
            source: Optional[str] = None,
            page: Optional[int] = None,
        ):
            """Retrieve information to help answer a query.
            You can filter the search results using metadata:
            - main_category: 대분류 (e.g. "정보기술개발", "정보기술관리", "직업기초능력")
            - sub_category: 중분류 (e.g. "SW아키텍쳐", "응용SW엔지니어링", "임베디드SW엔지니어링", "IT테스트", "IT품질보증", "IT프로젝트관리", "문제해결능력", "수리능력", "의사소통능력")
            - source: 원본 파일명 (e.g. "LM2001020101_SW아키텍처수행관리.pdf")
            - page: 특정 페이지 번호
            """
            # 필터 구성
            filter_dict = {}
            if main_category is not None:
                filter_dict["main_category"] = {"$eq": main_category}
            if sub_category is not None:
                filter_dict["sub_category"] = {"$eq": sub_category}
            if source is not None:
                filter_dict["source"] = {"$eq": source}
            if page is not None:
                filter_dict["page"] = {"$eq": page}

            # 필터가 있으면 적용, 없으면 전체 검색
            if filter_dict:
                retrieved_docs = await store.asimilarity_search(
                    query, k=2, filter=filter_dict
                )
            else:
                retrieved_docs = await store.asimilarity_search(query, k=2)

            serialized = "\n\n".join(
                (f"Source: {doc.metadata}\nContent: {doc.page_content}")
                for doc in retrieved_docs
            )

            if not serialized:
                serialized = "No documents found matching the filter criteria."

            return serialized, retrieved_docs

        return [retrieve_context]
