from loader import DocumentLoader
from splitter import DocumentSplitter
from embeddings import EmbeddingModel
from vector_store import VectorStoreManager
from dotenv import load_dotenv
import asyncio
import os

# 환경 변수 로드
load_dotenv()

async def ingest_data():
    """PDF 데이터를 로드하고 벡터 저장소에 적재하는 함수 (Async)"""
    
    # 설정 값
    FILE_PATH = "../assets/sample2.pdf"
    DB_CONNECTION = "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db"
    TABLE_NAME = 'test_table'

    print(f"Starting ingestion process for {FILE_PATH}...")

    # 1. 문서 로드
    loader = DocumentLoader(file_path=FILE_PATH)
    docs = loader.load()
    print(f"Loaded {len(docs)} pages from PDF.")

    # 2. 문서 분할
    splitter = DocumentSplitter()
    splits = splitter.split_documents(docs)
    print(f"Split documents into {len(splits)} chunks.")

    # 3. 임베딩 모델 준비
    embedding_model = EmbeddingModel().get_embeddings()

    # 4. 벡터 저장소 초기화 및 저장 (Async)
    print("Initializing Vector Store (Async)...")
    vector_store_manager = await VectorStoreManager.create(
        connection_string=DB_CONNECTION,
        table_name=TABLE_NAME,
        embedding_model=embedding_model
    )
    
    # 문서 추가 (Async)
    await vector_store_manager.add_documents(splits)
    print("Successfully added documents to vector store.")

if __name__ == "__main__":
    asyncio.run(ingest_data())
