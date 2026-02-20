from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
from eval.evaluators import (
    make_faithfulness_evaluator,
    make_context_relevance_evaluator,
    make_correctness_evaluator,
    make_answer_relevance_evaluator,
    create_all_evaluators,
)


def _make_judge_model():
    return MagicMock()


# ── Faithfulness tests ──────────────────────────────────────────

def test_faithfulness_returns_1_when_factual():
    judge_model = _make_judge_model()
    evaluator = make_faithfulness_evaluator(judge_model)

    mock_result_df = pd.DataFrame([{"label": "factual", "score": 1}])
    with patch("eval.evaluators.run_evals", return_value=[mock_result_df]):
        score = evaluator(
            input={"question": "질문", "doc_id": "uuid"},
            output={"answer": "답변", "retrieved_context": "컨텍스트"},
            expected={"reference_answer": "정답"},
        )
    assert score == 1.0


def test_faithfulness_returns_0_when_hallucinated():
    judge_model = _make_judge_model()
    evaluator = make_faithfulness_evaluator(judge_model)

    mock_result_df = pd.DataFrame([{"label": "hallucinated", "score": 0}])
    with patch("eval.evaluators.run_evals", return_value=[mock_result_df]):
        score = evaluator(
            input={"question": "질문", "doc_id": "uuid"},
            output={"answer": "답변", "retrieved_context": "컨텍스트"},
            expected={"reference_answer": "정답"},
        )
    assert score == 0.0


# ── Context Relevance tests ─────────────────────────────────────

def test_context_relevance_returns_1_when_relevant():
    judge_model = _make_judge_model()
    evaluator = make_context_relevance_evaluator(judge_model)

    mock_result_df = pd.DataFrame([{"label": "relevant", "score": 1}])
    with patch("eval.evaluators.run_evals", return_value=[mock_result_df]):
        score = evaluator(
            input={"question": "질문", "doc_id": "uuid"},
            output={"answer": "답변", "retrieved_context": "컨텍스트"},
            expected={"reference_answer": "정답"},
        )
    assert score == 1.0


# ── Correctness tests ────────────────────────────────────────────

def test_correctness_returns_1_when_correct():
    judge_model = _make_judge_model()
    evaluator = make_correctness_evaluator(judge_model)

    mock_result_df = pd.DataFrame([{"label": "correct", "score": 1}])
    with patch("eval.evaluators.run_evals", return_value=[mock_result_df]):
        score = evaluator(
            input={"question": "질문", "doc_id": "uuid"},
            output={"answer": "맞는 답변", "retrieved_context": "컨텍스트"},
            expected={"reference_answer": "정답"},
        )
    assert score == 1.0


def test_correctness_returns_0_when_incorrect():
    judge_model = _make_judge_model()
    evaluator = make_correctness_evaluator(judge_model)

    mock_result_df = pd.DataFrame([{"label": "incorrect", "score": 0}])
    with patch("eval.evaluators.run_evals", return_value=[mock_result_df]):
        score = evaluator(
            input={"question": "질문", "doc_id": "uuid"},
            output={"answer": "틀린 답변", "retrieved_context": "컨텍스트"},
            expected={"reference_answer": "정답"},
        )
    assert score == 0.0


# ── Answer Relevance tests ──────────────────────────────────────

def test_answer_relevance_returns_1_when_relevant():
    judge_model = _make_judge_model()
    evaluator = make_answer_relevance_evaluator(judge_model)

    mock_df = pd.DataFrame([{"label": "relevant", "score": 1}])
    with patch("eval.evaluators.llm_classify", return_value=mock_df):
        score = evaluator(
            input={"question": "질문", "doc_id": "uuid"},
            output={"answer": "관련 답변", "retrieved_context": "컨텍스트"},
            expected={"reference_answer": "정답"},
        )
    assert score == 1.0


def test_answer_relevance_returns_0_when_irrelevant():
    judge_model = _make_judge_model()
    evaluator = make_answer_relevance_evaluator(judge_model)

    mock_df = pd.DataFrame([{"label": "irrelevant", "score": 0}])
    with patch("eval.evaluators.llm_classify", return_value=mock_df):
        score = evaluator(
            input={"question": "질문", "doc_id": "uuid"},
            output={"answer": "무관한 답변", "retrieved_context": "컨텍스트"},
            expected={"reference_answer": "정답"},
        )
    assert score == 0.0


# ── create_all_evaluators test ───────────────────────────────────

def test_create_all_evaluators_returns_four():
    judge_model = _make_judge_model()
    evaluators = create_all_evaluators(judge_model)
    assert len(evaluators) == 4
    for ev in evaluators:
        assert callable(ev)


def test_create_all_evaluators_names_are_unique():
    """각 평가기는 고유한 __name__을 가진다."""
    judge_model = _make_judge_model()
    evaluators = create_all_evaluators(judge_model)
    names = [ev.__name__ for ev in evaluators]
    assert len(names) == len(set(names)), "Evaluator names must be unique"
