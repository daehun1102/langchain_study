from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from semiconductor.tool import (
    inspect_photo_patterns, measure_photo_cd,
    inspect_etch_profile, measure_etch_depth,
    inspect_deposition_thickness, check_deposition_uniformity,
    generate_random_process_history
)

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

# 5. 라우터 에이전트 (공정 선택만 담당)
router_agent = create_agent(
    model,
    tools=[],
    system_prompt=(
        "너는 반도체 공정 라우터 에이전트야. 사용자가 제공한 LOT ID와 요청 사항을 보고 "
        "photo, etch, deposition 중 어떤 공정을 검사할지 결정해. "
        "반드시 하나의 공정만 선택하고, 'photo' / 'etch' / 'deposition' 중 하나를 "
        'JSON으로만 반환해. 예: {"process": "photo", "reason": "..."}'
    ),
)

# 6. 일반 대화(Chat) 에이전트
chat_agent = create_agent(
    model,
    tools=[],
    system_prompt=(
        "너는 반도체 FAB의 친절한 어시스턴트야. "
        "반도체 공정 검사 요청이 아닌 일반 대화에 응답해. "
        "사용자의 질문에 친절하고 간결하게 답변해줘. "
        "반도체 관련 일반 지식 질문에도 답변할 수 있어."
    ),
)

# 7. 관리자(Supervisor) 에이전트 (최종 요약만 담당)
supervisor_agent = create_agent(
    model,
    tools=[],
    system_prompt=(
        "너는 반도체 공정 에이전트야. 사용자가 제공한 LOT ID와 요청 사항을 보고 "
        "대화의 히스토리를 요약하고, 이력 정보와 사용자의 요청을 바탕으로 어떤 공정을 검사해야 할지 높은 레벨에서 정리하고, "
        "공정 검사 결과를 종합해 최종 답변을 만들어줘."
    ),
)
