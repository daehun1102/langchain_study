# ai_server/api/sessions.py
from fastapi import APIRouter, HTTPException

from ai_server.api.schemas import (
    SessionUpsertRequest,
    SessionSummary,
    SessionDetail,
    SessionTitleUpdate,
)
from ai_server.repositories import session_repo

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionSummary], response_model_by_alias=True)
async def list_sessions():
    rows = await session_repo.list_sessions()
    return [
        SessionSummary(
            id=r["id"],
            title=r["title"],
            product_id=r["product_id"],
            hypothesis=r["hypothesis"],
            agent_results=r["agent_results"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]


@router.get("/{id}", response_model=SessionDetail, response_model_by_alias=True)
async def get_session(id: str):
    row = await session_repo.get_session(id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionDetail(
        id=row["id"],
        title=row["title"],
        product_id=row["product_id"],
        defect_description=row["defect_description"],
        hypothesis=row["hypothesis"],
        agent_results=row["agent_results"],
        chat_messages=row["chat_messages"],
        enabled_agents=row["enabled_agents"],
        long_term_task_id=row["long_term_task_id"],
        long_term_status=row["long_term_status"],
        long_term_result=row["long_term_result"],
        final_action_plan=row["final_action_plan"],
        step=row["step"],
        hypotheses=row["hypotheses"],
        updated_at=row["updated_at"],
    )


@router.put("/{id}", response_model=SessionSummary, response_model_by_alias=True)
async def upsert_session(id: str, body: SessionUpsertRequest):
    data = body.model_dump()
    row = await session_repo.upsert_session(id, data)
    return SessionSummary(
        id=row["id"],
        title=row["title"],
        product_id=row["product_id"],
        hypothesis=row["hypothesis"],
        agent_results=row["agent_results"],
        updated_at=row["updated_at"],
    )


@router.delete("/{id}", status_code=204)
async def delete_session(id: str):
    # 멱등성(idempotent): 존재하지 않는 ID도 항상 204 반환
    await session_repo.delete_session(id)


@router.patch("/{id}/title", response_model=SessionSummary, response_model_by_alias=True)
async def update_session_title(id: str, body: SessionTitleUpdate):
    row = await session_repo.update_session_title(id, body.title)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionSummary(
        id=row["id"],
        title=row["title"],
        product_id=row["product_id"],
        hypothesis=row["hypothesis"],
        agent_results=row["agent_results"],
        updated_at=row["updated_at"],
    )
