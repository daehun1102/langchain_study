"""
vector_store.py — PGVectorStore 관리 모듈

변경 사항 (Phase 2):
- metadata_columns: doc_id + page만 사용
- similarity_search_by_doc_ids(): doc_id 목록으로 필터링 검색

변경 사항 (Phase 2.1):
- delete_by_doc_id(): doc_id 청크 일괄 삭제 (삭제 일관성)
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
        doc_ids: Optional[List[str]] = None,
        k: int = 4,
    ) -> List[Document]:
        """doc_id 목록 범위 내에서 유사도 검색을 수행한다.

        doc_ids가 비어있으면 전체 벡터에서 검색한다.
        """
        if doc_ids:
            filter_dict = {"doc_id": {"$in": doc_ids}}
            return await self.vector_store.asimilarity_search(query, k=k, filter=filter_dict)
        return await self.vector_store.asimilarity_search(query, k=k)

    async def delete_by_doc_id(self, doc_id: str) -> int:
        """doc_id에 해당하는 모든 벡터 청크를 삭제한다.

        langchain-postgres는 메타데이터 필터로 벡터 삭제 API를 제공하지 않으므로
        SQLAlchemy를 통해 직접 SQL DELETE를 실행한다.

        Args:
            doc_id: Oracle documents 테이블의 doc_id (UUID)

        Returns:
            삭제된 청크(행) 수
        """
        from sqlalchemy import text
        engine = self.pg_engine._engine
        async with engine.begin() as conn:
            result = await conn.execute(
                text(f"DELETE FROM {TABLE_NAME} WHERE doc_id = :doc_id"),
                {"doc_id": doc_id},
            )
            return result.rowcount

    def get_vector_store(self):
        return self.vector_store
