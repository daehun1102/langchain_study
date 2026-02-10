from typing import Annotated, Literal, TypedDict
import operator


class AgentInput(TypedDict):
    """각 서브 에이전트를 위한 간단한 입력 상태입니다."""
    query: str


class AgentOutput(TypedDict):
    """각 서브 에이전트의 출력입니다."""
    source: str
    result: str


class Classification(TypedDict):
    """단일 라우팅 결정: 어떤 쿼리로 어떤 에이전트를 호출할지 결정합니다."""
    source: Literal["photo", "etch", "deposition", "history"]
    query: str


class RouterState(TypedDict):
    query: str
    classifications: list[Classification]
    results: Annotated[list[AgentOutput], operator.add] 
    final_answer: str
