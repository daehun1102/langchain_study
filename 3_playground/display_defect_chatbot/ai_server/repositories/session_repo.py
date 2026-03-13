# ai_server/repositories/session_repo.py
import json
from typing import Optional

from sqlalchemy import text

from ai_server.infra.database import get_db_session


async def upsert_session(id: str, data: dict) -> dict:
    params = {**data, "id": id}
    params["agent_results"] = json.dumps(data["agent_results"])
    params["chat_messages"] = json.dumps(data["chat_messages"])
    params["enabled_agents"] = json.dumps(data["enabled_agents"])
    params["hypotheses"] = json.dumps(data.get("hypotheses", []))

    async with get_db_session() as session:
        result = await session.execute(
            text("""
                INSERT INTO chat_sessions (
                    id, title, product_id, defect_description, hypothesis,
                    agent_results, chat_messages, enabled_agents,
                    long_term_task_id, long_term_status, long_term_result,
                    final_action_plan, step, hypotheses
                ) VALUES (
                    :id, :title, :product_id, :defect_description, :hypothesis,
                    CAST(:agent_results AS jsonb), CAST(:chat_messages AS jsonb), CAST(:enabled_agents AS jsonb),
                    :long_term_task_id, :long_term_status, :long_term_result,
                    :final_action_plan, :step, CAST(:hypotheses AS jsonb)
                )
                ON CONFLICT (id) DO UPDATE SET
                    title               = EXCLUDED.title,
                    product_id          = EXCLUDED.product_id,
                    defect_description  = EXCLUDED.defect_description,
                    hypothesis          = EXCLUDED.hypothesis,
                    agent_results       = EXCLUDED.agent_results,
                    chat_messages       = EXCLUDED.chat_messages,
                    enabled_agents      = EXCLUDED.enabled_agents,
                    long_term_task_id   = EXCLUDED.long_term_task_id,
                    long_term_status    = EXCLUDED.long_term_status,
                    long_term_result    = EXCLUDED.long_term_result,
                    final_action_plan   = EXCLUDED.final_action_plan,
                    step                = EXCLUDED.step,
                    hypotheses          = EXCLUDED.hypotheses,
                    updated_at          = NOW()
                RETURNING id, title, product_id, hypothesis, agent_results, updated_at
            """),
            params,
        )
        row = result.mappings().first()
        if row is None:
            raise RuntimeError(f"upsert_session: RETURNING produced no row for id={id!r}")
        return dict(row)


async def list_sessions() -> list[dict]:
    async with get_db_session() as session:
        result = await session.execute(
            text("""
                SELECT id, title, product_id, hypothesis, agent_results, updated_at
                FROM chat_sessions
                ORDER BY updated_at DESC
            """)
        )
        return [dict(r) for r in result.mappings().all()]


async def get_session(id: str) -> Optional[dict]:
    async with get_db_session() as session:
        result = await session.execute(
            text("""
                SELECT id, title, product_id, defect_description, hypothesis,
                       agent_results, chat_messages, enabled_agents,
                       long_term_task_id, long_term_status, long_term_result,
                       final_action_plan, step, hypotheses, updated_at
                FROM chat_sessions
                WHERE id = :id
            """),
            {"id": id},
        )
        row = result.mappings().first()
        return dict(row) if row else None


async def delete_session(id: str) -> None:
    async with get_db_session() as session:
        await session.execute(
            text("DELETE FROM chat_sessions WHERE id = :id"),
            {"id": id},
        )


async def update_session_title(id: str, title: str) -> Optional[dict]:
    """Returns updated summary row (id, title, product_id, hypothesis, agent_results, updated_at),
    or None if session not found."""
    async with get_db_session() as session:
        result = await session.execute(
            text("""
                UPDATE chat_sessions
                SET title = :title, updated_at = NOW()
                WHERE id = :id
                RETURNING id, title, product_id, hypothesis, agent_results, updated_at
            """),
            {"id": id, "title": title},
        )
        row = result.mappings().first()
        return dict(row) if row else None
