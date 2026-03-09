# display_defect_chatbot/ai_server/tools/sql_tools.py
from sqlalchemy import text
from ai_server.infra.database import get_db_session
from typing import Any, Optional
from datetime import datetime


# ── 공통 헬퍼 ────────────────────────────────────────────────

async def _query_by_product_id(sql: str, product_id: str) -> list[dict[str, Any]]:
    """product_id 기준 단순 조회 → list[dict] 반환"""
    async with get_db_session() as session:
        result = await session.execute(text(sql), {"pid": product_id})
        return [dict(r) for r in result.mappings().all()]


# ── SQL 상수 ─────────────────────────────────────────────────

_PROCESS_HISTORY_SQL = """
    SELECT process_step, equipment_id, operator_id, result, measured_at
    FROM process_history
    WHERE product_id = :pid
    ORDER BY measured_at DESC
    LIMIT 20
"""

_RETURN_HISTORY_SQL = """
    SELECT return_reason, return_date, quantity, severity
    FROM return_history
    WHERE product_id = :pid
    ORDER BY return_date DESC
    LIMIT 10
"""

_TEST_RESULTS_SQL = """
    SELECT test_type, result, measured_value, spec_min, spec_max, tested_at
    FROM test_results
    WHERE product_id = :pid
    ORDER BY tested_at DESC
    LIMIT 20
"""


# ── 서브에이전트 조회 함수 ───────────────────────────────────

async def query_process_history(product_id: str) -> list[dict[str, Any]]:
    """공정이력 테이블 조회"""
    return await _query_by_product_id(_PROCESS_HISTORY_SQL, product_id)


async def query_return_history(product_id: str) -> list[dict[str, Any]]:
    """반송이력 테이블 조회"""
    return await _query_by_product_id(_RETURN_HISTORY_SQL, product_id)


async def query_test_results(product_id: str) -> list[dict[str, Any]]:
    """테스트결과 테이블 조회"""
    return await _query_by_product_id(_TEST_RESULTS_SQL, product_id)


async def query_long_term_history(product_id: str) -> str:
    """장기 이력 분석 (모델 기준 최근 6개월 불량 통계)

    products 조회 + 통계 조회를 단일 JOIN 쿼리로 합산.
    """
    async with get_db_session() as session:
        stats = await session.execute(
            text("""
                SELECT p.model, ph.process_step,
                       COUNT(*) AS total,
                       SUM(CASE WHEN ph.result = 'FAIL' THEN 1 ELSE 0 END) AS fail_count
                FROM process_history ph
                JOIN products p ON ph.product_id = p.product_id
                WHERE p.model = (SELECT model FROM products WHERE product_id = :pid)
                  AND ph.measured_at >= NOW() - INTERVAL '6 months'
                GROUP BY p.model, ph.process_step
                ORDER BY fail_count DESC
            """),
            {"pid": product_id},
        )
        rows = stats.mappings().all()

    model = rows[0]["model"] if rows else "UNKNOWN"
    lines = [f"[장기 이력 분석] 모델: {model}", "공정별 불량 통계 (최근 6개월):"]
    for r in rows:
        rate = (r["fail_count"] / r["total"] * 100) if r["total"] > 0 else 0
        lines.append(f"  {r['process_step']}: {r['fail_count']}/{r['total']} ({rate:.1f}% FAIL)")

    return "\n".join(lines)


# ── background_tasks 테이블 조작 ─────────────────────────────

async def insert_bg_task(task_id: str, session_id: str) -> None:
    """백그라운드 태스크 PENDING 레코드 삽입"""
    async with get_db_session() as session:
        await session.execute(
            text("""
                INSERT INTO background_tasks (task_id, session_id, status)
                VALUES (:task_id, :session_id, 'PENDING')
            """),
            {"task_id": task_id, "session_id": session_id},
        )


async def complete_bg_task(task_id: str, result_text: str) -> None:
    """백그라운드 태스크 COMPLETED 업데이트"""
    async with get_db_session() as session:
        await session.execute(
            text("""
                UPDATE background_tasks
                SET status = 'COMPLETED', result_text = :result, completed_at = :now
                WHERE task_id = :task_id
            """),
            {"task_id": task_id, "result": result_text, "now": datetime.now()},
        )


async def fail_bg_task(task_id: str) -> None:
    """백그라운드 태스크 FAILED 업데이트"""
    async with get_db_session() as session:
        await session.execute(
            text("UPDATE background_tasks SET status = 'FAILED' WHERE task_id = :task_id"),
            {"task_id": task_id},
        )


async def get_bg_task(task_id: str) -> Optional[dict]:
    """백그라운드 태스크 상태 조회"""
    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT task_id, status, result_text FROM background_tasks WHERE task_id = :tid"),
            {"tid": task_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None
