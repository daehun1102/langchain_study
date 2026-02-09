from langchain_community.document_loaders import PyPDFLoader
from langchain_upstage import UpstageDocumentParseLoader
from typing import List
from langchain_core.documents import Document

class DocumentLoader:
    """기본 PDF 파일을 로드하는 클래스 (PyPDFLoader 사용)"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> List[Document]:
        """PDF 파일을 로드하여 문서 리스트를 반환합니다."""
        loader = PyPDFLoader(self.file_path)
        return loader.load()

class UpstageLoader:
    """Upstage Document Parse Loader를 사용하는 클래스"""

    def __init__(self, file_path: str, split: str = "page"):
        self.file_path = file_path
        self.split = split

    def load(self) -> List[Document]:
        """Upstage Loader를 사용하여 문서를 로드합니다."""
        loader = UpstageDocumentParseLoader(self.file_path, split=self.split)
        return loader.load()
