from agents.v1.sql_agent import SqlAgent
from agents.v1.supervisor import SupervisorAgent

__all__ = ["ChatAgent", "SqlAgent", "SupervisorAgent"]


def __getattr__(name):
    if name == "ChatAgent":
        from agents.v1.rag_agent import ChatAgent
        return ChatAgent
    raise AttributeError(f"module 'agents' has no attribute {name!r}")
