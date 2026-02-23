"""
run_evaluation.py — RAG 버전별 평가 실험 실행 진입점

실행 예:
    cd ai_server
    python -m eval.run_evaluation --datasets v1 --agents v1_baseline v2_gpt4o
    python -m eval.run_evaluation --datasets v1 v2 --agents v1_baseline v2_gpt4o v3_k8
"""

import asyncio
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

from eval.configs import (
    DatasetConfig, RAGConfig,
    DATASET_V1, DATASET_V2,
    V1_BASELINE, V2_GPT4O, V3_K8,
)
from eval.create_dataset import create_dataset
from eval.tasks import make_task
from eval.evaluators import create_all_evaluators

_DATASET_REGISTRY = {"v1": DATASET_V1, "v2": DATASET_V2}
_AGENT_REGISTRY = {"v1_baseline": V1_BASELINE, "v2_gpt4o": V2_GPT4O, "v3_k8": V3_K8}


def build_experiment_matrix(
    dataset_configs: list[DatasetConfig],
    rag_configs: list[RAGConfig],
) -> list[tuple[str, DatasetConfig, RAGConfig]]:
    """(experiment_name, dataset_config, rag_config) 조합 목록을 반환한다."""
    matrix = []
    for ds in dataset_configs:
        for rag in rag_configs:
            name = f"{rag.version}_on_{ds.name}"
            matrix.append((name, ds, rag))
    return matrix


def get_or_create_dataset(
    dataset_config: DatasetConfig,
    phoenix_client,
    db_connection: str,
):
    """Phoenix에서 데이터셋을 가져오거나 없으면 새로 생성한다."""
    try:
        dataset = phoenix_client.datasets.get_dataset(dataset=dataset_config.name)
        logger.info("[eval] 기존 데이터셋 로드: %s", dataset_config.name)
        return dataset
    except Exception:
        logger.info("[eval] 데이터셋 없음. 생성 시작: %s", dataset_config.name)
        asyncio.run(create_dataset(dataset_config, db_connection=db_connection))
        return phoenix_client.datasets.get_dataset(dataset=dataset_config.name)


def run_all(
    dataset_keys: list[str],
    agent_keys: list[str],
    db_connection: str,
    phoenix_endpoint: str = "http://localhost:6006",
    judge_model_name: str = "gpt-4o",
):
    """지정된 조합으로 전체 실험을 실행한다."""
    from phoenix.client import Client
    from phoenix.evals import OpenAIModel
    from phoenix.experiments import run_experiment

    dataset_configs = [_DATASET_REGISTRY[k] for k in dataset_keys]
    rag_configs = [_AGENT_REGISTRY[k] for k in agent_keys]
    matrix = build_experiment_matrix(dataset_configs, rag_configs)

    print(f"\n실험 매트릭스: {len(matrix)}개 조합")
    for name, _, _ in matrix:
        print(f"  - {name}")
    print()

    phoenix_client = Client(base_url=phoenix_endpoint)
    judge_model = OpenAIModel(model=judge_model_name, temperature=0.0)
    evaluators = create_all_evaluators(judge_model)

    for i, (exp_name, ds_config, rag_config) in enumerate(matrix, 1):
        print(f"[{i}/{len(matrix)}] 실험 시작: {exp_name}")
        dataset = get_or_create_dataset(ds_config, phoenix_client, db_connection)
        task_fn = make_task(rag_config, db_connection=db_connection)

        results = run_experiment(
            dataset=dataset,
            task=task_fn,
            evaluators=evaluators,
            experiment_name=exp_name,
        )
        print(f"       완료 → Phoenix UI: {phoenix_endpoint}")

    print(f"\n모든 실험 완료. 결과 확인: {phoenix_endpoint}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG 버전별 평가 실험 실행")
    parser.add_argument(
        "--datasets", nargs="+", choices=list(_DATASET_REGISTRY.keys()), required=True
    )
    parser.add_argument(
        "--agents", nargs="+", choices=list(_AGENT_REGISTRY.keys()), required=True
    )
    parser.add_argument(
        "--db",
        default=os.getenv("DB_CONNECTION", "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db"),
    )
    parser.add_argument("--phoenix", default="http://localhost:6006")
    parser.add_argument("--judge", default="gpt-4o")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    run_all(
        dataset_keys=args.datasets,
        agent_keys=args.agents,
        db_connection=args.db,
        phoenix_endpoint=args.phoenix,
        judge_model_name=args.judge,
    )
