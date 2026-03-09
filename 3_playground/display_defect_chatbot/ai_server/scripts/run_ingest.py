"""
RAG 문서 ingest 스크립트

실행 방법 (프로젝트 루트 display_defect_chatbot/ 에서):
    python -m ai_server.scripts.run_ingest

로컬 개발 시 .env의 POSTGRES_HOST=localhost, POSTGRES_PORT=5433 확인
"""
import asyncio
import os
import sys

# 프로젝트 루트(display_defect_chatbot/)를 sys.path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from langchain_openai import OpenAIEmbeddings
from ai_server.config import get_settings
from ai_server.infra.vector_store import VectorStoreManager
from ai_server.infra.ingest import ingest_document

MOCK_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "mock_data")

DOCUMENTS = {
    "display_failure_cases":      "display_failure_cases.txt",
    "oled_amoled_failure_cases":  "oled_amoled_failure_cases.txt",
    "equipment_sop":              "equipment_sop.txt",
    "quality_standards":          "quality_standards.txt",
    "corrective_action_guide":    "corrective_action_guide.txt",
    "process_failure_history":    "process_failure_history.txt",
}


async def main():
    s = get_settings()
    print(f"Connecting to: {s.postgres_host}:{s.postgres_port}/{s.postgres_db}")

    emb = OpenAIEmbeddings(model=s.embedding_model, api_key=s.openai_api_key)
    vsm = await VectorStoreManager.create(s.pg_async_url, emb)

    for doc_id, filename in DOCUMENTS.items():
        file_path = os.path.join(MOCK_DATA_DIR, filename)
        if not os.path.exists(file_path):
            print(f"[SKIP] {filename} not found")
            continue
        count = await ingest_document(doc_id, file_path, vsm)
        print(f"[OK]   {doc_id}: {count} chunks ingested")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
