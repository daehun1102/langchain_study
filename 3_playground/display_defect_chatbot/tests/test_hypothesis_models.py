# tests/test_hypothesis_models.py
import pytest
from pydantic import ValidationError
from ai_server.agents.state import HypothesisItem, HypothesesResponse


def test_hypothesis_item_valid():
    item = HypothesisItem(
        text="가설1: 공정 오염 — 증착 공정 중 파티클 유입",
        recommended_agents=["process_history", "test_result"],
    )
    assert item.text == "가설1: 공정 오염 — 증착 공정 중 파티클 유입"
    assert item.recommended_agents == ["process_history", "test_result"]


def test_hypothesis_item_model_dump():
    item = HypothesisItem(
        text="가설2: 전극 단선",
        recommended_agents=["return_history"],
    )
    d = item.model_dump()
    assert d == {"text": "가설2: 전극 단선", "recommended_agents": ["return_history"]}


def test_hypotheses_response_valid():
    resp = HypothesesResponse(
        hypotheses=[
            HypothesisItem(text="가설1", recommended_agents=["process_history"]),
            HypothesisItem(text="가설2", recommended_agents=["return_history", "long_term"]),
        ]
    )
    assert len(resp.hypotheses) == 2
    assert resp.hypotheses[0].text == "가설1"


def test_hypotheses_response_missing_field_raises():
    with pytest.raises(ValidationError):
        HypothesesResponse()


def test_hypothesis_item_invalid_agent_rejected():
    """유효하지 않은 에이전트명은 ValidationError 발생"""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        HypothesisItem(text="가설1", recommended_agents=["invalid_agent"])


def test_hypothesis_item_empty_recommended_agents():
    """빈 recommended_agents 리스트는 허용됨 (LLM이 빈 목록 반환할 수 있음)"""
    item = HypothesisItem(text="가설1", recommended_agents=[])
    assert item.recommended_agents == []
