import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unittest.mock import MagicMock, patch
import pytest
from eval.configs import DATASET_V1, V1_BASELINE
from eval.run_evaluation import build_experiment_matrix, get_or_create_dataset


# ── 실험 매트릭스 테스트 ─────────────────────────────────────────

def test_build_experiment_matrix_cartesian_product():
    from eval.configs import DATASET_V1, DATASET_V2, V1_BASELINE, V2_GPT4O
    matrix = build_experiment_matrix(
        dataset_configs=[DATASET_V1, DATASET_V2],
        rag_configs=[V1_BASELINE, V2_GPT4O],
    )
    assert len(matrix) == 4
    names = [exp_name for exp_name, _, _ in matrix]
    assert "v1_baseline_on_ncs-rag-eval-v1" in names
    assert "v2_gpt4o_on_ncs-rag-eval-v2" in names


def test_build_experiment_matrix_name_format():
    matrix = build_experiment_matrix(
        dataset_configs=[DATASET_V1],
        rag_configs=[V1_BASELINE],
    )
    exp_name, ds_cfg, rag_cfg = matrix[0]
    assert exp_name == f"{rag_cfg.version}_on_{ds_cfg.name}"


# ── get_or_create_dataset 테스트 ─────────────────────────────────

def test_get_or_create_dataset_returns_existing():
    """Phoenix에 이미 데이터셋이 있으면 그대로 반환한다."""
    mock_client = MagicMock()
    mock_dataset = MagicMock()
    mock_client.get_dataset.return_value = mock_dataset

    result = get_or_create_dataset(DATASET_V1, mock_client, db_connection="test_db")

    mock_client.get_dataset.assert_called_once_with(name=DATASET_V1.name)
    assert result == mock_dataset


def test_get_or_create_dataset_creates_when_not_found():
    """데이터셋이 없으면 create_dataset을 실행한다."""
    mock_client = MagicMock()
    mock_client.get_dataset.side_effect = Exception("Not found")

    with patch("eval.run_evaluation.asyncio") as mock_asyncio, \
         patch("eval.run_evaluation.create_dataset") as mock_create:
        mock_asyncio.run = MagicMock()
        mock_client.get_dataset.side_effect = [Exception("Not found"), MagicMock()]
        get_or_create_dataset(DATASET_V1, mock_client, db_connection="test_db")

    mock_asyncio.run.assert_called_once()
