from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from typing import List
import sys
import io

# Windows 콘솔 인코딩 문제 해결
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

class ChatAgent:
    """채팅 에이전트를 생성하고 실행하는 클래스"""

    def __init__(self, model_name: str = "gpt-4o-mini", system_prompt: str = None):
        self.model = init_chat_model(model_name)
        if system_prompt is None:
            self.system_prompt = (
                "너는 NCS(국가직무능력표준) 문서에서 정보를 검색하여 답변해주는 친절한 AI 어시스턴트야.\n"
                "사용자의 질의에 retrieve_context 도구를 적극적으로 사용해서 답변해줘.\n\n"
                "## 메타데이터 필터링 가이드\n"
                "retrieve_context 도구는 다음 필터를 지원해:\n"
                "- main_category (대분류): '정보기술개발', '정보기술관리', '직업기초능력'\n"
                "- sub_category (중분류): 'SW아키텍쳐', '응용SW엔지니어링', '임베디드SW엔지니어링', "
                "'IT테스트', 'IT품질보증', 'IT프로젝트관리', '문제해결능력', '수리능력', '의사소통능력'\n"
                "- source: 원본 파일명\n"
                "- page: 특정 페이지 번호 (정수)\n\n"
                "사용자가 특정 분야, 카테고리, 또는 페이지를 언급하면 "
                "해당 필터를 사용하여 검색 범위를 좁혀줘. "
                "필터를 사용하면 소량의 관련 데이터에서만 검색하므로 더 정확한 결과를 얻을 수 있어."
            )
        else:
            self.system_prompt = system_prompt

    def create_agent(self, tools: List):
        """모델과 도구를 결합하여 에이전트를 생성합니다."""
        self.agent = create_agent(self.model, tools, system_prompt=self.system_prompt)
    
    async def run(self, query: str):
        """사용자 질의를 처리하고 답변을 생성합니다. (Async)"""
        if not hasattr(self, 'agent'):
            raise ValueError("Agent has not been created. Call create_agent() first.")

        print(f"User Query: {query}")
        print("--- Agent Response ---")
        
        last_message = None
        # astream을 사용하여 비동기 스트리밍 처리
        async for event in self.agent.astream(
            {"messages": [{"role": "user", "content": query}]},
            stream_mode="values",
        ):
            event["messages"][-1].pretty_print()
            last_message = event["messages"][-1]
        
        return last_message
