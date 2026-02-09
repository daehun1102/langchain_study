from embeddings import EmbeddingModel
from vector_store import VectorStoreManager
from tool import ToolBuilder
from agent import ChatAgent
from dotenv import load_dotenv
import asyncio

# 환경 변수 로드
load_dotenv()

async def main():
    """챗봇 실행 메인 함수 (Async)"""
    
    # 설정 값
    DB_CONNECTION = "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db"
    TABLE_NAME = 'test_table'
    
    print("Initializing Chatbot...")

    # 1. 임베딩 모델 & 벡터 저장소 연결 (Async)
    embedding_model = EmbeddingModel().get_embeddings()
    vector_store_manager = await VectorStoreManager.create(
        connection_string=DB_CONNECTION,
        table_name=TABLE_NAME,
        embedding_model=embedding_model

    )
    vector_store = vector_store_manager.get_vector_store()

    # 2. 도구 생성 (벡터 저장소가 async 지원하므로 tool 내부에서도 비동기 호출)
    tool_builder = ToolBuilder(vector_store)
    tools = tool_builder.build_tools()

    # 3. 에이전트 생성 및 실행
    agent = ChatAgent()
    agent.create_agent(tools)
    
    # 테스트 질의 (Async)
    query = ""
    await agent.run(query)

if __name__ == "__main__":
    asyncio.run(main())
