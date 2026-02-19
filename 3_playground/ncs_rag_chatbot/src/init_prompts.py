"""
init_prompts.py — Redis에 초기 프롬프트 데이터를 등록하는 스크립트

실행: python src/init_prompts.py
Redis가 실행 중이어야 합니다 (docker run -d -p 6379:6379 redis)
"""

import redis
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
PREFIX = "prompt:"

PROMPTS = {
    "agent_system_prompt": (
        "너는 NCS(국가직무능력표준) 문서에서 정보를 검색하여 답변해주는 친절한 AI 어시스턴트야.\n"
        "사용자의 질의에 retrieve_context 도구를 적극적으로 사용해서 답변해줘.\n"
        "답변할 때 검색된 문서의 내용을 바탕으로 정확하게 답변하고, "
        "관련 내용의 페이지 정보를 언급해줘."
    ),
}

if __name__ == "__main__":
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    for key, value in PROMPTS.items():
        r.set(PREFIX + key, value)
        print(f"[init_prompts] 저장 완료: {PREFIX + key}")
    print(f"\n총 {len(PROMPTS)}개 프롬프트 등록 완료")
    print("확인: redis-cli get prompt:agent_system_prompt")
