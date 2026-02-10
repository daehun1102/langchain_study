from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from src.semiconductor.tool import (
    inspect_photo_patterns, measure_photo_cd,
    inspect_etch_profile, measure_etch_depth,
    inspect_deposition_thickness, check_deposition_uniformity,
    generate_random_process_history
)
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.tools import tool

model = init_chat_model("openai:gpt-4o-mini")

# 1. 포토(Photo) 공정 에이전트
photo_agent = create_agent(
    model,
    tools=[inspect_photo_patterns, measure_photo_cd],
    system_prompt=(
        "너는 반도체 포토(Photo) 공정 검사 전문가야. "
        "LOT 번호를 받아 패턴 검사나 CD 측정을 수행해."
    ),
)

# 2. 식각(Etch) 공정 에이전트
etch_agent = create_agent(
    model,
    tools=[inspect_etch_profile, measure_etch_depth],
    system_prompt=(
        "너는 반도체 식각(Etch) 공정 검사 전문가야. "
        "LOT 번호를 받아 식각 프로파일이나 깊이를 측정해."
    ),
)

# 3. 증착(Deposition) 공정 에이전트
deposition_agent = create_agent(
    model,
    tools=[inspect_deposition_thickness, check_deposition_uniformity],
    system_prompt=(
        "너는 반도체 증착(Deposition) 공정 검사 전문가야. "
        "LOT 번호를 받아 막 두께나 균일도를 검사해."
    ),
)



# 4. 이력(History) 에이전트
history_agent = create_agent(
    model,
    tools=[generate_random_process_history],
    system_prompt=(
        "너는 반도체 공정 이력 관리 전문가야. "
        "LOT 번호를 받아 해당 LOT의 전체 공정 이력을 조회(생성)해."
    ),
)

@tool
def create_photo_agent(request: str) -> str:
    """
    포토(Photo) 공정 에이전트를 생성하고 요청을 위임합니다.
    """
    result = photo_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].content

@tool
def create_etch_agent(request: str) -> str:
    """
    식각(Etch) 공정 에이전트를 생성하고 요청을 위임합니다.
    """
    result = etch_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].content

@tool
def create_deposition_agent(request: str) -> str:
    """
    증착(Deposition) 공정 에이전트를 생성하고 요청을 위임합니다.
    """
    result = deposition_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].content

@tool
def create_history_agent(request: str) -> str:
    """
    이력(History) 에이전트를 생성하고 요청을 위임합니다.
    """
    result = history_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].content


router_agent = create_agent(
    model,
    tools=[create_photo_agent, create_etch_agent, create_deposition_agent],
    system_prompt=(
        "너는 반도체 공정 라우터 에이전트야. 사용자가 제공한 LOT ID와 요청 사항을 보고 "
        "포토, 식각, 증착 에이전트 중 적절한 곳으로 위임해. "
        "도구는 [create_photo_agent, create_etch_agent, create_deposition_agent] 이야. "
        "예를 들어 LOT 번호나 문맥에서 공정을 유추할 수 있어. "
        "반드시 한번에 한개의 에이전트만 호출해."
    ),
    middleware=[HumanInTheLoopMiddleware(
        interrupt_on={
            "create_photo_agent": True,
            "create_etch_agent": True,
            "create_deposition_agent": True,
        }
    )]
)

@tool
def create_router_agent(request: str) -> str:
    """
    요청을 받아서 photo, etch, deposition 중 적절한 에이전트를 호출하고 요청을 위임합니다.
    """
    result = router_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].content

# 관리자(Supervisor) 에이전트
supervisor_agent = create_agent(
    model,
    tools=[create_router_agent, create_history_agent],
    system_prompt=(
        "너는 반도체 공정 에이전트야. 사용자가 제공한 LOT ID와 요청 사항을 보고 "
        "먼저 이력 에이전트(create_history_agent)를 호출해 공정 이력을 파악한 뒤, "
        "해당 이력과 사용자의 요청을 기준으로 photo, etch, deposition 중 어떤 공정을 검사할지 결정해."
        "그 다음, 라우터 에이전트(create_router_agent)를 호출할 때는, "
        " LOT ID와 어떤 공정을 어떤 방식으로 검사해야 하는지가 포함된 한국어 문장을 request 문자열로 전달해."
        "예: 'LOT ABC123의 photo 공정 패턴을 검사해줘.' 와 같이 자연어 요청을 만들어."
        "반드시 한 번에 한 개의 에이전트만 호출해."
    )
)
