# display_defect_chatbot/ai_server/infra/ingest.py
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from ai_server.infra.vector_store import VectorStoreManager


async def ingest_document(doc_id: str, file_path: str, vsm: VectorStoreManager) -> int:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(content)

    docs = [
        Document(
            page_content=chunk,
            metadata={"doc_id": doc_id, "chunk_index": i},
        )
        for i, chunk in enumerate(chunks)
    ]

    await vsm.vector_store.aadd_documents(docs)
    return len(docs)
