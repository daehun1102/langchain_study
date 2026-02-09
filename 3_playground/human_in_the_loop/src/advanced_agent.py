from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from src.tool import search_code, search_issues, search_prs, search_notion, get_page, search_slack, get_thread
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.tools import tool

model = init_chat_model("openai:gpt-4o-mini")

github_agent = create_agent(
    model,
    tools=[search_code, search_issues, search_prs],
    system_prompt=(
        "너는 깃허브 전문가야. 코드, API 레퍼런스, 구현 세부사항에 대해 질문하면 "
        "리포지토리, 이슈, 풀 리퀘스트를 검색해서 대답해."
    ),
)

notion_agent = create_agent(
    model,
    tools=[search_notion, get_page],
    system_prompt=(
        "너는 노션 전문가야. 내부 프로세스, 정책, 팀 문서에 대해 질문하면 "
        "노션 워크스페이스를 검색해서 대답해."
    ),
)

slack_agent = create_agent(
    model,
    tools=[search_slack, get_thread],
    system_prompt=(
        "너는 슬랙 전문가야. 팀원들이 지식과 해결책을 공유한 "
        "관련 스레드와 토론을 검색해서 대답해."
    ),
)

@tool
def create_github_agent(request: str) -> str:
    """
    GitHub 에이전트를 생성하고 사용자의 질문을 위임합니다.
    """
    result = github_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text

@tool
def create_notion_agent(request: str) -> str:
    """
    Notion 에이전트를 생성하고 사용자의 질문을 위임합니다.
    """
    result = notion_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text

@tool
def create_slack_agent(request: str) -> str:
    """
    Slack 에이전트를 생성하고 사용자의 질문을 위임합니다.
    """
    result = slack_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text

supervisor_agent = create_agent(
    model,
    tools=[create_github_agent, create_notion_agent, create_slack_agent],
    system_prompt=(
        "너는 라우터 에이전트야. 사용자의 질문을 분석하고 "
        "어떤 에이전트한테 위임할지 결정해."
    ),
    middleware=[HumanInTheLoopMiddleware(
        interrupt_on={
            "create_github_agent": True,
            "create_notion_agent": True,
            "create_slack_agent": True
        }
    )]
)