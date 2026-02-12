from langchain_postgres import PGEngine, PGVectorStore, PGVector, Column
from typing import List, Optional
from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import ProgrammingError

class VectorStoreManager:
    """벡터 저장소(PostgreSQL)를 관리하는 클래스 (Async)"""

    def __init__(self, engine, vector_store):
        self.pg_engine = engine
        self.vector_store = vector_store

    @classmethod
    async def create(
        cls,
        connection_string: str,
        table_name: str,
        embedding_model,
        metadata_columns: Optional[List[str]] = None,
    ):
        """비동기적으로 VectorStoreManager 인스턴스를 생성합니다."""
        engine = create_async_engine(connection_string)
        pg_engine = PGEngine.from_engine(engine)

        if metadata_columns:
            vector_store = await PGVectorStore.create(
                engine=pg_engine,
                table_name=table_name,
                embedding_service=embedding_model,
                metadata_columns=metadata_columns,
            )
        else:
            vector_store = await PGVectorStore.create(
                engine=pg_engine,
                table_name=table_name,
                embedding_service=embedding_model,
            )

        return cls(pg_engine, vector_store)

    async def init_table(self, table_name: str, vector_size: int, metadata_columns: List[Column]):
        """메타데이터 컬럼이 포함된 벡터 저장소 테이블을 초기화합니다."""
        await self.pg_engine.ainit_vectorstore_table(
            table_name=table_name,
            vector_size=vector_size,
            metadata_columns=metadata_columns,
        )

    async def add_documents(self, documents: List[Document]):
        """문서를 벡터 저장소에 추가합니다. (비동기)"""
        return await self.vector_store.aadd_documents(documents=documents)

    def get_vector_store(self):
        """벡터 저장소 객체를 반환합니다."""
        return self.vector_store
    
    def as_retriever(self, search_kwargs: dict = None):
        """Retriever 인터페이스로 변환합니다."""
        if search_kwargs is None:
            search_kwargs = {"k": 2}
        return self.vector_store.as_retriever(search_kwargs=search_kwargs)
