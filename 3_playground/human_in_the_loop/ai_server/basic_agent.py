from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import MemorySaver
from langchain.tools import tool

@tool
def send_email(to: str, subject: str, body: str):
    """Send an email"""
    email = {
        "to": to,
        "subject": subject,
        "body": body
    }

    return f"Email sent to {to}"

basic_agent = create_agent(
    "gpt-4o-mini",
    tools=[send_email],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "send_email": True, # 인터럽트시 사용자에게 approve, edit, reject 세가지 권한을 모두 줍니다. 
                # "send_email": {"allowed_decisions": ["approve", "reject"]},
                # "send_email": False, # 인터럽트시 사용자에게 어떠한 권한도 주지 않습니다.
            },
            description_prefix="승인이 필요합니다: "
        )
    ],
    system_prompt="You are an email assistant. Always use the send_email tool.",
)
