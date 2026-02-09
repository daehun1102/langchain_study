from langchain_postgres import PGEngine, PGVectorStore, PGVector
from typing import List
from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import ProgrammingError

class VectorStoreManager:
    """벡터 저장소(PostgreSQL)를 관리하는 클래스 (Async)"""

    def __init__(self, engine, vector_store):
        self.pg_engine = engine
        self.vector_store = vector_store

    @classmethod
    async def create(cls, connection_string: str, table_name: str, embedding_model):
        """비동기적으로 VectorStoreManager 인스턴스를 생성합니다."""
        engine = create_async_engine(connection_string)
        pg_engine = PGEngine.from_engine(engine)
        
        vector_store = await PGVectorStore.create(
            engine=pg_engine,
            table_name=table_name,
            embedding_service=embedding_model
        )
        
        return cls(pg_engine, vector_store)

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
