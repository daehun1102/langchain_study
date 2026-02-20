import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from eval.configs import DatasetConfig, RAGConfig, DATASET_V1, DATASET_V2, V1_BASELINE, V2_GPT4O, V3_K8


def test_dataset_config_fields():
    cfg = DatasetConfig(
        name="test-dataset",
        version="v1",
        num_samples=10,
        generation_strategy="factual",
        categories=None,
    )
    assert cfg.name == "test-dataset"
    assert cfg.num_samples == 10
    assert cfg.generation_strategy == "factual"
    assert cfg.categories is None


def test_rag_config_fields():
    cfg = RAGConfig(
        version="v1_baseline",
        model_name="gpt-4o-mini",
        retrieval_k=4,
        prompt_override=None,
    )
    assert cfg.version == "v1_baseline"
    assert cfg.retrieval_k == 4
    assert cfg.prompt_override is None


def test_default_instances_exist():
    assert DATASET_V1.generation_strategy == "factual"
    assert DATASET_V2.generation_strategy == "mixed"
    assert V1_BASELINE.model_name == "gpt-4o-mini"
    assert V2_GPT4O.model_name == "gpt-4o"
    assert V3_K8.retrieval_k == 8


def test_rag_config_prompt_override():
    cfg = RAGConfig(
        version="v_custom",
        model_name="gpt-4o-mini",
        retrieval_k=4,
        prompt_override={"agent_system_prompt": "custom prompt"},
    )
    assert cfg.prompt_override["agent_system_prompt"] == "custom prompt"
