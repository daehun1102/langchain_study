"""
init_prompts.py — Redis에 초기 프롬프트 데이터를 등록하는 스크립트

실행: python ai_server/init_prompts.py
Redis가 실행 중이어야 합니다.
"""

import redis
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
PREFIX = "prompt:"

PROMPTS = {
    "agent_system_prompt": (
        "너는 NCS(국가직무능력표준) 문서에서 정보를 검색하여 답변해주는 친절한 AI 어시스턴트야.\n"
        "사용자의 질의에 항상 retrieve_context 도구를 사용해서 먼저 관련 문서를 검색하고 답변해줘.\n"
        "문서에서 찾은 내용만 답변하고, 모르는 내용은 추측하지 마."
    ),
    "answer_format_prompt": (
        "답변 형식 지침:\n"
        "- 마크다운 형식으로 작성해줘 (헤딩, 목록, 굵게 등 적극 활용)\n"
        "- 답변 말미에 출처를 명시해줘: '출처: 페이지 {페이지번호}'\n"
        "- 여러 문서에서 정보를 가져왔다면 각 내용의 출처를 구분해서 표시해줘\n"
        "- 불확실한 내용은 반드시 '문서에서 확인되지 않음'이라고 표시해줘"
    ),
    "no_document_prompt": (
        "관련 문서를 찾지 못했을 때 안내:\n"
        "retrieve_context 도구로 검색했으나 관련 내용을 찾지 못한 경우, 다음과 같이 안내해줘:\n"
        "'해당 카테고리에 등록된 문서에서 관련 내용을 찾을 수 없습니다. "
        "다른 카테고리를 선택하거나, 질문을 좀 더 구체적으로 바꿔보세요.'"
    ),
    "query_enhance_prompt": (
        "검색 쿼리 최적화 지침:\n"
        "- 사용자 질의가 짧거나 모호하면 NCS 문서 맥락에 맞게 구체화하여 검색해줘\n"
        "- 예: '테스트란?' → 'NCS IT테스트 기획 및 설계 방법'\n"
        "- 첫 검색 결과가 불충분하면 다른 키워드로 재검색해줘 (최대 2회)\n"
        "- 검색어는 한국어로 작성해줘"
    ),
    "category_hint_prompt": (
        "카테고리 안내:\n"
        "카테고리가 선택되지 않아 전체 문서에서 검색합니다.\n"
        "답변 말미에 다음 문구를 추가해줘:\n"
        "'💡 좌측 카테고리 필터를 선택하면 특정 분야의 문서만 검색하여 더 정확한 답변을 받을 수 있습니다.'"
    ),
}

if __name__ == "__main__":
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    try:
        r.ping()
    except redis.ConnectionError:
        print(f"[ERROR] Redis에 연결할 수 없습니다: {REDIS_HOST}:{REDIS_PORT}")
        raise SystemExit(1)

    for key, value in PROMPTS.items():
        r.set(PREFIX + key, value)
        print(f"[init_prompts] 저장 완료: {PREFIX + key}")

    print(f"\n총 {len(PROMPTS)}개 프롬프트 등록 완료")
    print("확인: redis-cli keys 'prompt:*'")
