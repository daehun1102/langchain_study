import asyncio
from uuid import uuid4
from datetime import datetime
from sqlalchemy import text

from ai_server.tools.sql_tools import query_long_term_history
from ai_server.infra.database import get_db_session


async def long_term_node(state: dict) -> dict:
    """장기이력 에이전트: 백그라운드로 실행, 즉시 task_id 반환"""
    task_id = str(uuid4())
    product_id = state.get("product_id", "")
    session_id = state.get("session_id", "")
    hypothesis = state.get("selected_hypothesis", "")

    # DB에 PENDING 레코드 삽입
    async with get_db_session() as session:
        await session.execute(
            text("""
                INSERT INTO background_tasks (task_id, session_id, status)
                VALUES (:task_id, :session_id, 'PENDING')
            """),
            {"task_id": task_id, "session_id": session_id},
        )

    # 백그라운드 태스크 시작 (논블로킹)
    asyncio.create_task(_run_long_term_analysis(task_id, product_id, hypothesis))

    return {"long_term_task_id": [task_id]}


async def _run_long_term_analysis(task_id: str, product_id: str, hypothesis: str):
    """장기 이력 분석 실행 (수 초 ~ 수십 초 소요 시뮬레이션)"""
    await asyncio.sleep(10)  # Mock: 실제 분석 시간 시뮬레이션

    try:
        result_text = await query_long_term_history(product_id)
        result_text += f"\n\n[선택된 가설에 기반한 추가 분석]\n{hypothesis}를 중심으로 6개월 추이를 분석한 결과, 재발 방지를 위한 공정 파라미터 조정이 필요합니다."

        async with get_db_session() as session:
            await session.execute(
                text("""
                    UPDATE background_tasks
                    SET status = 'COMPLETED', result_text = :result, completed_at = :now
                    WHERE task_id = :task_id
                """),
                {"task_id": task_id, "result": result_text, "now": datetime.now()},
            )
    except Exception as e:
        async with get_db_session() as session:
            await session.execute(
                text("UPDATE background_tasks SET status = 'FAILED' WHERE task_id = :task_id"),
                {"task_id": task_id},
            )
