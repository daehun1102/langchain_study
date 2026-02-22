from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from eval.configs import DatasetConfig
from eval.create_dataset import (
    fetch_chunks,
    generate_qa_pair,
    build_qa_prompt,
)


# ── fetch_chunks 테스트 ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_chunks_returns_list_of_dicts():
    """fetch_chunks가 {document, doc_id} 딕셔너리 목록을 반환한다."""
    mock_rows = [
        MagicMock(content="청크1 내용", doc_id="uuid-001"),
        MagicMock(content="청크2 내용", doc_id="uuid-002"),
    ]
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = mock_rows

    with patch("eval.create_dataset.create_async_engine") as mock_engine_cls:
        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_engine.dispose = AsyncMock()

        result = await fetch_chunks(db_connection="postgresql+asyncpg://test", num_samples=2)

    assert len(result) == 2
    assert result[0]["document"] == "청크1 내용"
    assert result[0]["doc_id"] == "uuid-001"


# ── build_qa_prompt 테스트 ──────────────────────────────────────

def test_build_qa_prompt_factual_contains_chunk():
    prompt = build_qa_prompt(chunk="테스트 청크 내용", strategy="factual")
    assert "테스트 청크 내용" in prompt
    assert "사실" in prompt or "factual" in prompt.lower()


def test_build_qa_prompt_reasoning_contains_chunk():
    prompt = build_qa_prompt(chunk="테스트 청크 내용", strategy="reasoning")
    assert "테스트 청크 내용" in prompt
    assert "추론" in prompt or "reasoning" in prompt.lower()


def test_build_qa_prompt_mixed_uses_factual_or_reasoning(monkeypatch):
    import random
    monkeypatch.setattr(random, "choice", lambda x: x[0])
    prompt = build_qa_prompt(chunk="청크", strategy="mixed")
    assert "청크" in prompt


# ── generate_qa_pair 테스트 ─────────────────────────────────────

def test_generate_qa_pair_returns_question_and_answer():
    """LLM 응답에서 question, reference_answer를 파싱한다."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        '{"question": "테스트 질문?", "reference_answer": "테스트 답변"}'
    )
    mock_client.chat.completions.create.return_value = mock_response

    result = generate_qa_pair(
        chunk="청크 내용",
        strategy="factual",
        client=mock_client,
        model="gpt-4o",
    )

    assert result["question"] == "테스트 질문?"
    assert result["reference_answer"] == "테스트 답변"


def test_generate_qa_pair_returns_none_on_invalid_json():
    """LLM 응답이 JSON 파싱 불가이면 None을 반환한다."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "유효하지 않은 응답"
    mock_client.chat.completions.create.return_value = mock_response

    result = generate_qa_pair(
        chunk="청크", strategy="factual", client=mock_client, model="gpt-4o"
    )
    assert result is None


def test_generate_qa_pair_returns_none_on_missing_keys():
    """JSON이지만 필수 키가 없으면 None을 반환한다."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"question": "질문만 있음"}'
    mock_client.chat.completions.create.return_value = mock_response

    result = generate_qa_pair(
        chunk="청크", strategy="factual", client=mock_client, model="gpt-4o"
    )
    assert result is None
