"""
prompt_loader.py — Redis에서 프롬프트 템플릿을 로드하는 모듈

Spring의 PromptService가 저장한 "prompt:<key>" 형식의 키를 읽는다.
Redis 연결 실패 시 fallback 기본값을 반환한다.
"""

import os
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
PREFIX = "prompt:"

# Redis 연결 실패 시 사용하는 기본 프롬프트
FALLBACK_PROMPTS = {
    "agent_system_prompt": (
        "너는 NCS(국가직무능력표준) 문서에서 정보를 검색하여 답변해주는 친절한 AI 어시스턴트야.\n"
        "사용자의 질의에 retrieve_context 도구를 적극적으로 사용해서 답변해줘.\n"
        "답변할 때 검색된 문서의 내용을 바탕으로 정확하게 답변하고, "
        "관련 내용의 페이지 정보를 언급해줘."
    ),
}


def get_prompt(key: str) -> str:
    """Redis에서 프롬프트를 가져온다. 실패 시 fallback을 반환한다."""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        value = r.get(PREFIX + key)
        if value:
            return value
        # Redis에 키가 없으면 fallback 반환
        return FALLBACK_PROMPTS.get(key, "")
    except Exception as e:
        import logging
        logging.getLogger("prompt_loader").warning(
            "Redis 연결 실패, fallback 사용: %s", e
        )
        return FALLBACK_PROMPTS.get(key, "")
