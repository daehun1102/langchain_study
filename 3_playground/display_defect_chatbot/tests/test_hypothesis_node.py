# tests/test_hypothesis_node.py
"""
hypothesis_node의 structured output 변환 로직 단위 테스트.
Task 3 Step 3 이후 graph.py import 검증 포함 (red-green TDD).
"""
import pytest
from ai_server.agents.state import HypothesisItem, HypothesesResponse


def make_mock_response():
    return HypothesesResponse(
        hypotheses=[
            HypothesisItem(
                text="가설1: 공정 오염 — 증착 챔버 파티클",
                recommended_agents=["process_history", "test_history"],
            ),
            HypothesisItem(
                text="가설2: 전극 단선 — 식각 과도",
                recommended_agents=["return_history", "process_history"],
            ),
        ]
    )


def test_model_dump_produces_correct_list():
    """model_dump()로 state 저장 형식(list[dict]) 변환 검증"""
    resp = make_mock_response()
    hypotheses_data = [h.model_dump() for h in resp.hypotheses]

    assert len(hypotheses_data) == 2
    assert hypotheses_data[0]["text"] == "가설1: 공정 오염 — 증착 챔버 파티클"
    assert hypotheses_data[0]["recommended_agents"] == ["process_history", "test_history"]


def test_interrupt_payload_has_required_keys():
    """interrupt 페이로드가 text와 recommended_agents 키를 포함하는지 검증"""
    resp = make_mock_response()
    hypotheses_data = [h.model_dump() for h in resp.hypotheses]
    payload = {"hypotheses": hypotheses_data}

    assert isinstance(payload["hypotheses"], list)
    assert "text" in payload["hypotheses"][0]
    assert "recommended_agents" in payload["hypotheses"][0]


def test_resume_dict_extracts_correctly():
    """resume dict에서 selected_hypothesis, enabled_agents 추출 검증"""
    resume = {
        "selected_hypothesis": "가설1: 공정 오염",
        "enabled_agents": ["process_history", "test_history"],
    }
    assert resume.get("selected_hypothesis") == "가설1: 공정 오염"
    assert resume.get("enabled_agents") == ["process_history", "test_history"]


def test_hypothesis_llm_exists_in_graph():
    """graph.py에 _hypothesis_llm 모듈 레벨 변수가 존재하는지 검증 (Step 3 이후 green)"""
    from ai_server.agents import graph
    assert hasattr(graph, "_hypothesis_llm"), "_hypothesis_llm must be defined at module level"
