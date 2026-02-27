"""
ingest.py — PDF를 PGVector에 적재하는 모듈

변경 사항 (Phase 2):
- 메타데이터 컬럼을 doc_id + page로 단순화 (Oracle과 doc_id로 연결)
- ingest_single_document(): Spring에서 단일 PDF 처리 요청 시 호출
"""

from infra.loader import DocumentLoader
from infra.splitter import DocumentSplitter
from infra.embeddings import EmbeddingModel
from infra.vector_store import TABLE_NAME
from langchain_postgres import PGEngine, PGVectorStore, Column
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()
VECTOR_SIZE = 1536  # text-embedding-3-small

# PGVector에는 doc_id(Oracle 참조)와 page만 저장
METADATA_COLUMNS = [
    Column("doc_id", "VARCHAR", nullable=True),
    Column("page", "INTEGER", nullable=True),
]


async def _get_pg_engine(db_connection: str):
    engine = create_async_engine(db_connection)
    return PGEngine.from_engine(engine)


async def _get_vector_store(pg_engine, embedding_model):
    return await PGVectorStore.create(
        engine=pg_engine,
        table_name=TABLE_NAME,
        embedding_service=embedding_model,
        metadata_columns=["doc_id", "page"],
    )


async def init_table(db_connection: str):
    """테이블을 초기화한다. 최초 1회 또는 스키마 변경 시 실행."""
    pg_engine = await _get_pg_engine(db_connection)
    await pg_engine.ainit_vectorstore_table(
        table_name=TABLE_NAME,
        vector_size=VECTOR_SIZE,
        metadata_columns=METADATA_COLUMNS,
        overwrite_existing=True,
    )
    print(f"[ingest] 테이블 '{TABLE_NAME}' 초기화 완료")


async def ingest_single_document(doc_id: str, file_path: str, db_connection: str) -> int:
    """단일 PDF를 PGVector에 적재한다.

    Args:
        doc_id: Oracle documents 테이블의 PK (UUID)
        file_path: PDF 파일 절대 경로
        db_connection: PGVector 연결 문자열

    Returns:
        저장된 청크 수
    """
    embedding_model = EmbeddingModel().get_embeddings()
    pg_engine = await _get_pg_engine(db_connection)
    vector_store = await _get_vector_store(pg_engine, embedding_model)

    loader = DocumentLoader(file_path=file_path)
    docs = loader.load()

    splitter = DocumentSplitter()
    splits = splitter.split_documents(docs)

    for doc in splits:
        doc.page_content = doc.page_content.replace("\x00", "")
        doc.metadata["doc_id"] = doc_id
        doc.metadata["page"] = doc.metadata.get("page", 0)

    await vector_store.aadd_documents(splits)
    print(f"[ingest] doc_id={doc_id}, 청크={len(splits)}개 저장 완료")
    return len(splits)


if __name__ == "__main__":
    import sys
    db = os.getenv("DB_CONNECTION", "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db")

    if len(sys.argv) == 2 and sys.argv[1] == "init":
        # 테이블 초기화: python ingest.py init
        asyncio.run(init_table(db))
    elif len(sys.argv) == 3:
        # 단일 파일 ingest: python ingest.py <doc_id> <file_path>
        asyncio.run(ingest_single_document(sys.argv[1], sys.argv[2], db))
    else:
        print("Usage:")
        print("  python -m infra.ingest init               # 테이블 초기화")
        print("  python -m infra.ingest <doc_id> <path>    # 단일 파일 적재")
