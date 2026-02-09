from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

class EmbeddingModel:
    """임베딩 모델을 관리하는 클래스"""

    def __init__(self, model_name: str = "text-embedding-3-small"):
        self.embeddings = OpenAIEmbeddings(model=model_name)

    def get_embeddings(self):
        """LangChain 임베딩 객체를 반환합니다."""
        return self.embeddings
