from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List
from langchain_core.documents import Document

class DocumentSplitter:
    """문서를 청크로 분할하는 클래스"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True,
        )

    def split_documents(self, docs: List[Document]) -> List[Document]:
        """문서 리스트를 받아 청크로 분할하여 반환합니다."""
        return self.text_splitter.split_documents(docs)
