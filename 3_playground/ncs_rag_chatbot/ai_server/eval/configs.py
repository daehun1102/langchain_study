"""
configs.py — 평가 시스템의 버전 설정 정의

DatasetConfig: 합성 데이터셋 생성 설정 (버전, 샘플 수, 생성 전략)
RAGConfig: RAG 에이전트 버전 설정 (모델, 검색 k, 프롬프트 오버라이드)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DatasetConfig:
    name: str                          # Phoenix dataset 이름 (예: "ncs-rag-eval-v1")
    version: str                       # 버전 레이블 (예: "v1")
    num_samples: int                   # 생성할 Q&A 쌍 총 개수
    generation_strategy: str           # "factual" | "reasoning" | "mixed"
    categories: Optional[list] = None  # None = 전체, 특정 값 = 필터링 (미구현, None만 사용)


@dataclass
class RAGConfig:
    version: str                              # 버전 레이블 (예: "v1_baseline")
    model_name: str                           # LLM 모델명 (예: "gpt-4o-mini")
    retrieval_k: int                          # similarity search top-k
    prompt_override: Optional[dict] = None    # None = Redis 로드, dict = 키별 오버라이드


# ── 기본 Dataset 버전 ───────────────────────────────────────────
DATASET_V1 = DatasetConfig(
    name="ncs-rag-eval-v1",
    version="v1",
    num_samples=50,
    generation_strategy="factual",
    categories=None,
)

DATASET_V2 = DatasetConfig(
    name="ncs-rag-eval-v2",
    version="v2",
    num_samples=100,
    generation_strategy="mixed",
    categories=None,
)

# ── 기본 RAG 버전 ────────────────────────────────────────────────
V1_BASELINE = RAGConfig(
    version="v1_baseline",
    model_name="gpt-4o-mini",
    retrieval_k=4,
    prompt_override=None,
)

V2_GPT4O = RAGConfig(
    version="v2_gpt4o",
    model_name="gpt-4o",
    retrieval_k=4,
    prompt_override=None,
)

V3_K8 = RAGConfig(
    version="v3_k8",
    model_name="gpt-4o-mini",
    retrieval_k=8,
    prompt_override=None,
)
