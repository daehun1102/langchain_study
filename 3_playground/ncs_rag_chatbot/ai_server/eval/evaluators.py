"""
evaluators.py — run_experiment() 용 평가 지표 4개 정의

각 evaluator 시그니처: (input: dict, output: dict, expected: dict) -> float

input    = {"question": str, "doc_id": str}
output   = {"answer": str, "retrieved_context": str}  ← task 반환값
expected = {"reference_answer": str}                   ← dataset output
"""

import pandas as pd
from phoenix.evals import (
    HallucinationEvaluator,
    QAEvaluator,
    RelevanceEvaluator,
    llm_classify,
    run_evals,
)

_ANSWER_RELEVANCE_TEMPLATE = """\
당신은 RAG 시스템의 답변 품질을 평가하는 전문가입니다.

[질문]: {question}
[답변]: {answer}

답변이 질문에 실질적으로 답하고 있습니까?
- relevant: 질문의 핵심에 명확히 답변함
- irrelevant: 질문을 회피하거나 무관한 내용을 답함

반드시 "relevant" 또는 "irrelevant" 중 하나만 출력하세요."""


def make_faithfulness_evaluator(judge_model):
    """Faithfulness: 답변이 검색된 컨텍스트에 근거하는지 평가한다."""
    _evaluator = HallucinationEvaluator(judge_model)

    def faithfulness(input: dict, output: dict, expected: dict) -> float:
        df = pd.DataFrame([{
            "input": input["question"],
            "output": output.get("answer", ""),
            "reference": output.get("retrieved_context", ""),
        }])
        results = run_evals(df, evaluators=[_evaluator], provide_explanation=True)
        return float(results[0]["score"].iloc[0])

    faithfulness.__name__ = "faithfulness"
    return faithfulness


def make_context_relevance_evaluator(judge_model):
    """Context Relevance: 검색된 컨텍스트가 질문에 관련있는지 평가한다."""
    _evaluator = RelevanceEvaluator(judge_model)

    def context_relevance(input: dict, output: dict, expected: dict) -> float:
        df = pd.DataFrame([{
            "input": input["question"],
            "reference": output.get("retrieved_context", ""),
        }])
        results = run_evals(df, evaluators=[_evaluator], provide_explanation=True)
        return float(results[0]["score"].iloc[0])

    context_relevance.__name__ = "context_relevance"
    return context_relevance


def make_correctness_evaluator(judge_model):
    """Correctness: 답변이 reference_answer와 일치하는지 평가한다."""
    _evaluator = QAEvaluator(judge_model)

    def correctness(input: dict, output: dict, expected: dict) -> float:
        df = pd.DataFrame([{
            "input": input["question"],
            "output": output.get("answer", ""),
            "reference": expected.get("reference_answer", ""),
        }])
        results = run_evals(df, evaluators=[_evaluator], provide_explanation=True)
        return float(results[0]["score"].iloc[0])

    correctness.__name__ = "correctness"
    return correctness


def make_answer_relevance_evaluator(judge_model):
    """Answer Relevance: 답변이 질문에 직접 답하는지 평가한다 (custom)."""

    def answer_relevance(input: dict, output: dict, expected: dict) -> float:
        df = pd.DataFrame([{
            "question": input["question"],
            "answer": output.get("answer", ""),
        }])
        results = llm_classify(
            dataframe=df,
            template=_ANSWER_RELEVANCE_TEMPLATE,
            model=judge_model,
            rails=["relevant", "irrelevant"],
            provide_explanation=True,
        )
        label = results["label"].iloc[0]
        return 1.0 if label == "relevant" else 0.0

    answer_relevance.__name__ = "answer_relevance"
    return answer_relevance


def create_all_evaluators(judge_model) -> list:
    """4개 평가 지표를 모두 생성해 반환한다."""
    return [
        make_faithfulness_evaluator(judge_model),
        make_context_relevance_evaluator(judge_model),
        make_correctness_evaluator(judge_model),
        make_answer_relevance_evaluator(judge_model),
    ]
