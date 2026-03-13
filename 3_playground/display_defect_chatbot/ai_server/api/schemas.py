# ai_server/api/schemas.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SessionUpsertRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    title: str
    product_id: str
    defect_description: str
    hypothesis: str
    agent_results: dict
    chat_messages: list
    enabled_agents: dict
    long_term_task_id: Optional[str] = None
    long_term_status: str
    long_term_result: Optional[str] = None
    final_action_plan: str


class SessionSummary(BaseModel):
    """목록 조회용 — 포함 필드: id, title, product_id, hypothesis, agent_results, updated_at
    제외 필드: defect_description, chat_messages, enabled_agents, long_term_*, final_action_plan, created_at"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    title: str
    product_id: str
    hypothesis: str
    agent_results: dict
    updated_at: datetime


class SessionDetail(BaseModel):
    """단건 조회용 — 포함 필드: id~updated_at (14개), 제외 필드: created_at"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    title: str
    product_id: str
    defect_description: str
    hypothesis: str
    agent_results: dict
    chat_messages: list
    enabled_agents: dict
    long_term_task_id: Optional[str] = None
    long_term_status: str
    long_term_result: Optional[str] = None
    final_action_plan: str
    updated_at: datetime


class SessionTitleUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    title: str
