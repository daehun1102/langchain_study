"""
vector_store.py — PGVectorStore 관리 모듈

변경 사항 (Phase 2):
- metadata_columns: doc_id + page만 사용
- similarity_search_by_doc_ids(): doc_id 목록으로 필터링 검색
"""

from langchain_postgres import PGEngine, PGVectorStore
from typing import List, Optional
from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import create_async_engine

TABLE_NAME = "ncs_vectors"


class VectorStoreManager:

    def __init__(self, pg_engine, vector_store):
        self.pg_engine = pg_engine
        self.vector_store = vector_store

    @classmethod
    async def create(cls, connection_string: str, embedding_model):
        """VectorStoreManager 인스턴스를 비동기로 생성한다."""
        engine = create_async_engine(connection_string)
        pg_engine = PGEngine.from_engine(engine)
        vector_store = await PGVectorStore.create(
            engine=pg_engine,
            table_name=TABLE_NAME,
            embedding_service=embedding_model,
            metadata_columns=["doc_id", "page"],
        )
        return cls(pg_engine, vector_store)

    async def similarity_search_by_doc_ids(
        self,
        query: str,
        doc_ids: List[str],
        k: int = 4,
    ) -> List[Document]:
        """doc_id 목록 범위 내에서 유사도 검색을 수행한다.

        doc_ids가 비어있으면 전체 벡터에서 검색한다.
        """
        if doc_ids:
            filter_dict = {"doc_id": {"$in": doc_ids}}
            return await self.vector_store.asimilarity_search(query, k=k, filter=filter_dict)
        return await self.vector_store.asimilarity_search(query, k=k)

    def get_vector_store(self):
        return self.vector_store
