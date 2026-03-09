# ai_server/infra/checkpointer.py
from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


@asynccontextmanager
async def checkpointer_lifespan(pg_url: str):
    """AsyncPostgresSaver 수명 관리 — lifespan 안에서 async with 로 사용.
    진입 시 체크포인트 테이블을 자동 생성하고, 종료 시 연결을 정리합니다.
    """
    async with AsyncPostgresSaver.from_conn_string(pg_url) as checkpointer:
        await checkpointer.setup()
        yield checkpointer
