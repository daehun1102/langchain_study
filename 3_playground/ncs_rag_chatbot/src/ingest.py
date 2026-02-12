from loader import DocumentLoader
from splitter import DocumentSplitter
from embeddings import EmbeddingModel
from langchain_postgres import PGEngine, PGVectorStore, Column
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv
import asyncio
import os
import glob

# 환경 변수 로드
load_dotenv()

# 메타데이터 컬럼 정의
METADATA_COLUMNS = [
    Column("main_category", "VARCHAR", nullable=True),   # 대분류: 정보기술개발, 정보기술관리, 직업기초능력
    Column("sub_category", "VARCHAR", nullable=True),     # 중분류: SW아키텍쳐, IT테스트 등
    Column("source", "VARCHAR", nullable=True),           # 원본 파일명
    Column("page", "INTEGER", nullable=True),             # 페이지 번호
]

# PDF 루트 디렉토리
ASSETS_ROOT = "../assets/실습 NCS파일"


def collect_pdf_files(root_dir: str):
    """폴더 구조에서 PDF 파일을 탐색하고 메타데이터를 추출합니다.

    폴더 구조: root/대분류/중분류/파일.pdf
    """
    pdf_entries = []

    for main_cat in os.listdir(root_dir):
        main_cat_path = os.path.join(root_dir, main_cat)
        if not os.path.isdir(main_cat_path):
            continue

        for sub_cat in os.listdir(main_cat_path):
            sub_cat_path = os.path.join(main_cat_path, sub_cat)
            if not os.path.isdir(sub_cat_path):
                continue

            for filename in os.listdir(sub_cat_path):
                if filename.lower().endswith(".pdf"):
                    pdf_entries.append({
                        "file_path": os.path.join(sub_cat_path, filename),
                        "main_category": main_cat,
                        "sub_category": sub_cat,
                        "source": filename,
                    })

    return pdf_entries


async def ingest_data():
    """PDF 데이터를 로드하고 벡터 저장소에 적재하는 함수 (Async)"""

    # 설정 값
    DB_CONNECTION = "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db"
    TABLE_NAME = "test_table_filtered"
    VECTOR_SIZE = 1536  # text-embedding-3-small 차원

    # 임베딩 모델 준비
    embedding_model = EmbeddingModel().get_embeddings()

    # 1. PGEngine 생성
    print("Initializing PGEngine...")
    engine = create_async_engine(DB_CONNECTION)
    pg_engine = PGEngine.from_engine(engine)

    # 2. 테이블 생성 (메타데이터 컬럼 포함)
    print(f"Creating table '{TABLE_NAME}' with metadata columns...")
    await pg_engine.ainit_vectorstore_table(
        table_name=TABLE_NAME,
        vector_size=VECTOR_SIZE,
        metadata_columns=METADATA_COLUMNS,
        overwrite_existing=True,
    )

    # 3. 벡터 저장소 연결
    print("Connecting to Vector Store...")
    vector_store = await PGVectorStore.create(
        engine=pg_engine,
        table_name=TABLE_NAME,
        embedding_service=embedding_model,
        metadata_columns=["main_category", "sub_category", "source", "page"],
    )

    # 4. PDF 파일 탐색
    pdf_entries = collect_pdf_files(ASSETS_ROOT)
    print(f"\nFound {len(pdf_entries)} PDF files:\n")
    for entry in pdf_entries:
        print(f"  [{entry['main_category']}] [{entry['sub_category']}] {entry['source']}")

    # 5. 문서 로드 및 적재
    splitter = DocumentSplitter()
    total_chunks = 0

    for entry in pdf_entries:
        print(f"\n--- Processing: {entry['source']} ---")
        print(f"  main_category: {entry['main_category']}")
        print(f"  sub_category:  {entry['sub_category']}")

        # 문서 로드
        loader = DocumentLoader(file_path=entry["file_path"])
        docs = loader.load()
        print(f"  Loaded {len(docs)} pages.")

        # 문서 분할
        splits = splitter.split_documents(docs)
        print(f"  Split into {len(splits)} chunks.")

        # 메타데이터 추가 + null byte 제거
        for doc in splits:
            doc.page_content = doc.page_content.replace("\x00", "")
            doc.metadata["main_category"] = entry["main_category"]
            doc.metadata["sub_category"] = entry["sub_category"]
            doc.metadata["source"] = entry["source"]
            doc.metadata["page"] = doc.metadata.get("page", 0)

        # 벡터 저장소에 추가
        await vector_store.aadd_documents(splits)
        total_chunks += len(splits)
        print(f"  Added {len(splits)} chunks.")

    print(f"\nIngestion complete! Total: {total_chunks} chunks from {len(pdf_entries)} files.")


if __name__ == "__main__":
    asyncio.run(ingest_data())
