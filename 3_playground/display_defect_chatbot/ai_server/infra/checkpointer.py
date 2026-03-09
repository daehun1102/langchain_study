# ai_server/infra/checkpointer.py
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


async def create_checkpointer(pg_url: str) -> AsyncPostgresSaver:
    """AsyncPostgresSaver 생성 및 LangGraph 체크포인트 테이블 자동 초기화."""
    checkpointer = AsyncPostgresSaver.from_conn_string(pg_url)
    await checkpointer.setup()  # checkpoints, checkpoint_blobs, checkpoint_writes 테이블 자동 생성
    return checkpointer
