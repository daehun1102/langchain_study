# display_defect_chatbot/ai_server/infra/vector_store.py
from langchain_postgres import PGEngine, PGVectorStore, Column
from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import ProgrammingError
from typing import List, Optional

TABLE_NAME = "defect_vectors"
VECTOR_SIZE = 1536  # text-embedding-3-small
METADATA_COLUMNS = [
    Column("doc_id", "VARCHAR", nullable=True),
    Column("chunk_index", "INTEGER", nullable=True),
]


class VectorStoreManager:
    def __init__(self, pg_engine, vector_store, engine):
        self.pg_engine = pg_engine
        self.vector_store = vector_store
        self._engine = engine  # public reference for raw SQL (avoids pg_engine._pool private API)

    @classmethod
    async def create(cls, connection_string: str, embedding_model):
        engine = create_async_engine(connection_string)
        pg_engine = PGEngine.from_engine(engine)
        try:
            await pg_engine.ainit_vectorstore_table(
                table_name=TABLE_NAME,
                vector_size=VECTOR_SIZE,
                metadata_columns=METADATA_COLUMNS,
                overwrite_existing=False,
            )
        except ProgrammingError as e:
            if "already exists" not in str(e.orig or e):
                raise
        vector_store = await PGVectorStore.create(
            engine=pg_engine,
            table_name=TABLE_NAME,
            embedding_service=embedding_model,
            metadata_columns=["doc_id", "chunk_index"],
        )
        return cls(pg_engine, vector_store, engine)

    async def similarity_search(self, query: str, doc_ids: Optional[List[str]] = None, k: int = 4) -> List[Document]:
        if doc_ids:
            return await self.vector_store.asimilarity_search(
                query, k=k, filter={"doc_id": {"$in": doc_ids}}
            )
        return await self.vector_store.asimilarity_search(query, k=k)

    async def delete_by_doc_id(self, doc_id: str) -> int:
        from sqlalchemy import text
        async with self._engine.begin() as conn:
            result = await conn.execute(
                text(f"DELETE FROM {TABLE_NAME} WHERE doc_id = :doc_id"),
                {"doc_id": doc_id},
            )
            return result.rowcount
