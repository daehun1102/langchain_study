"""
tracing.py — Arize Phoenix OpenTelemetry 트레이싱 설정

Phoenix가 실행 중이어야 한다:
  docker run -d --name arize-phoenix -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest

server.py 시작 시 setup_tracing()을 가장 먼저 호출하면
LangChain Agent의 모든 실행이 자동으로 트레이싱된다.

대시보드: http://localhost:6006
"""

import os
import logging

logger = logging.getLogger("ncs_tracing")

PHOENIX_HOST = os.getenv("PHOENIX_HOST")
PHOENIX_GRPC_PORT = os.getenv("PHOENIX_GRPC_PORT", "4317")


def setup_tracing() -> bool:
    """Arize Phoenix 트레이싱을 초기화한다.

    Phoenix 연결에 실패해도 서버 기동을 막지 않는다 (try/except).

    Returns:
        True: 트레이싱 활성화 성공
        False: 연결 실패 (서버는 계속 동작)
    """
    if not PHOENIX_HOST:
        return False

    try:
        from phoenix.otel import register
        from openinference.instrumentation.langchain import LangChainInstrumentor

        endpoint = f"http://{PHOENIX_HOST}:{PHOENIX_GRPC_PORT}"

        tracer_provider = register(
            project_name="ncs-rag-chatbot",
            endpoint=endpoint,
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

        logger.info("[tracing] Arize Phoenix 트레이싱 활성화: %s", endpoint)
        logger.info("[tracing] 대시보드: http://%s:6006", PHOENIX_HOST)
        return True

    except Exception as e:
        logger.warning("[tracing] Phoenix 연결 실패, 트레이싱 비활성화: %s", e)
        return False
