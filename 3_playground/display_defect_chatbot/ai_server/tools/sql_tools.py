# display_defect_chatbot/ai_server/tools/sql_tools.py
from sqlalchemy import text
from ai_server.infra.database import get_db_session
from typing import Any


async def query_process_history(product_id: str) -> list[dict[str, Any]]:
    """공정이력 테이블 조회"""
    async with get_db_session() as session:
        result = await session.execute(
            text("""
                SELECT process_step, equipment_id, operator_id, result, measured_at
                FROM process_history
                WHERE product_id = :pid
                ORDER BY measured_at DESC
                LIMIT 20
            """),
            {"pid": product_id},
        )
        rows = result.mappings().all()
        return [dict(r) for r in rows]


async def query_return_history(product_id: str) -> list[dict[str, Any]]:
    """반송이력 테이블 조회"""
    async with get_db_session() as session:
        result = await session.execute(
            text("""
                SELECT return_reason, return_date, quantity, severity
                FROM return_history
                WHERE product_id = :pid
                ORDER BY return_date DESC
                LIMIT 10
            """),
            {"pid": product_id},
        )
        rows = result.mappings().all()
        return [dict(r) for r in rows]


async def query_test_results(product_id: str) -> list[dict[str, Any]]:
    """테스트결과 테이블 조회"""
    async with get_db_session() as session:
        result = await session.execute(
            text("""
                SELECT test_type, result, measured_value, spec_min, spec_max, tested_at
                FROM test_results
                WHERE product_id = :pid
                ORDER BY tested_at DESC
                LIMIT 20
            """),
            {"pid": product_id},
        )
        rows = result.mappings().all()
        return [dict(r) for r in rows]


async def query_long_term_history(product_id: str) -> str:
    """장기 이력 분석 (모델 기준 6개월 불량 통계)"""
    async with get_db_session() as session:
        prod = await session.execute(
            text("SELECT model FROM products WHERE product_id = :pid"),
            {"pid": product_id},
        )
        product = prod.mappings().first()
        model = product["model"] if product else "UNKNOWN"

        stats = await session.execute(
            text("""
                SELECT ph.process_step,
                       COUNT(*) as total,
                       SUM(CASE WHEN ph.result = 'FAIL' THEN 1 ELSE 0 END) as fail_count
                FROM process_history ph
                JOIN products p ON ph.product_id = p.product_id
                WHERE p.model = :model
                GROUP BY ph.process_step
                ORDER BY fail_count DESC
            """),
            {"model": model},
        )
        rows = stats.mappings().all()

        lines = [f"[장기 이력 분석] 모델: {model}"]
        lines.append("공정별 불량 통계 (최근 6개월):")
        for r in rows:
            rate = (r["fail_count"] / r["total"] * 100) if r["total"] > 0 else 0
            lines.append(f"  {r['process_step']}: {r['fail_count']}/{r['total']} ({rate:.1f}% FAIL)")

        return "\n".join(lines)
