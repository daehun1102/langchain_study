"""
create_dataset.py — NCS 평가 데이터셋 생성 및 Phoenix 업로드

실행:
    cd ai_server
    python -m eval.create_dataset --config v1
    python -m eval.create_dataset --config v2
"""

import json
import random
import os
import asyncio
import logging
from typing import Any, Literal, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from eval.configs import DatasetConfig, DATASET_V1, DATASET_V2

logger = logging.getLogger(__name__)

_CONFIGS = {
    "v1": DATASET_V1,
    "v2": DATASET_V2,
}

TABLE_NAME = "ncs_vectors"


# ── SQL 쿼리 ────────────────────────────────────────────────────

async def fetch_chunks(db_connection: str, num_samples: int) -> list[dict]:
    """ncs_vectors 테이블에서 청크를 랜덤 샘플링한다.

    Returns:
        [{"document": str, "doc_id": str}, ...]
    """
    engine = create_async_engine(db_connection)
    async with engine.begin() as conn:
        rows = await conn.execute(
            text(
                f"SELECT content, doc_id FROM {TABLE_NAME} "
                "WHERE doc_id IS NOT NULL "
                "ORDER BY RANDOM() "
                "LIMIT :n"
            ),
            {"n": num_samples},
        )
    await engine.dispose()
    return [{"document": row.content, "doc_id": row.doc_id} for row in rows]


# ── Q&A 생성 ────────────────────────────────────────────────────

_FACTUAL_INSTRUCTION = (
    "문서에서 직접 찾을 수 있는 사실적인 질문을 생성하세요. "
    "답변은 문서 내용만을 근거로 작성하세요."
)

_REASONING_INSTRUCTION = (
    "문서를 읽고 추론·비교·적용이 필요한 심화 질문을 생성하세요. "
    "답변은 문서 내용을 바탕으로 논리적으로 작성하세요."
)


def build_qa_prompt(chunk: str, strategy: Literal["factual", "reasoning", "mixed"]) -> str:
    """strategy에 맞는 Q&A 생성 프롬프트를 반환한다."""
    if strategy == "mixed":
        instruction = random.choice([_FACTUAL_INSTRUCTION, _REASONING_INSTRUCTION])
    elif strategy == "reasoning":
        instruction = _REASONING_INSTRUCTION
    else:  # factual (default)
        instruction = _FACTUAL_INSTRUCTION

    return f"""당신은 NCS(국가직무능력표준) 교육 평가 전문가입니다.
아래 문서 청크를 읽고 질문-답변 쌍을 1개 생성하세요.

지침: {instruction}

[문서 청크]
{chunk}

반드시 아래 JSON 형식으로만 응답하세요:
{{"question": "질문 내용", "reference_answer": "답변 내용"}}"""


def generate_qa_pair(
    chunk: str,
    strategy: str,
    client: Any,
    model: str = "gpt-4o",
) -> Optional[dict]:
    """단일 청크에서 Q&A 쌍을 생성한다.

    Returns:
        {"question": str, "reference_answer": str} 또는 파싱 실패 시 None
    """
    prompt = build_qa_prompt(chunk, strategy)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    raw = response.choices[0].message.content
    try:
        data = json.loads(raw)
        if "question" not in data or "reference_answer" not in data:
            return None
        return data
    except json.JSONDecodeError:
        logger.warning("[create_dataset] Q&A 파싱 실패: %s", raw[:100])
        return None


# ── Phoenix 업로드 ───────────────────────────────────────────────

def upload_to_phoenix(
    config: DatasetConfig,
    qa_pairs: list[dict],
    chunks: list[dict],
    base_url: str = "http://localhost:6006",
) -> None:
    """생성된 Q&A 쌍을 Phoenix Dataset으로 업로드한다."""
    from phoenix.client import Client

    client = Client(base_url=base_url)
    inputs = [{"question": qa["question"], "doc_id": chunk["doc_id"]}
              for qa, chunk in zip(qa_pairs, chunks)]
    outputs = [{"reference_answer": qa["reference_answer"]} for qa in qa_pairs]
    metadata = [
        {
            "source_chunk": chunk["document"][:500],
            "generation_strategy": config.generation_strategy,
            "dataset_version": config.version,
        }
        for chunk in chunks
    ]

    dataset = client.datasets.create_dataset(
        name=config.name,
        inputs=inputs,
        outputs=outputs,
        metadata=metadata,
    )
    logger.info("[create_dataset] Phoenix 업로드 완료: %s (%d examples)", dataset.name, len(inputs))
    print(f"Dataset '{dataset.name}' uploaded: {len(inputs)} examples")


# ── 메인 실행 ────────────────────────────────────────────────────

async def create_dataset(config: DatasetConfig, db_connection: str, llm_model: str = "gpt-4o"):
    """데이터셋 생성 전체 파이프라인을 실행한다."""
    from openai import OpenAI

    print(f"[1/3] PGVector에서 {config.num_samples}개 청크 샘플링...")
    chunks = await fetch_chunks(db_connection, config.num_samples)
    print(f"      → {len(chunks)}개 청크 로드 완료")

    print(f"[2/3] LLM Q&A 합성 (strategy={config.generation_strategy})...")
    llm_client = OpenAI()
    qa_pairs = []
    valid_chunks = []
    for i, chunk in enumerate(chunks):
        result = generate_qa_pair(
            chunk=chunk["document"],
            strategy=config.generation_strategy,
            client=llm_client,
            model=llm_model,
        )
        if result is not None:
            qa_pairs.append(result)
            valid_chunks.append(chunk)
        if (i + 1) % 10 == 0:
            print(f"      {i + 1}/{len(chunks)} 처리 중...")
    print(f"      → {len(qa_pairs)}개 Q&A 생성 완료 (파싱 실패: {len(chunks) - len(qa_pairs)}개)")

    print(f"[3/3] Phoenix Dataset '{config.name}' 업로드...")
    upload_to_phoenix(config, qa_pairs, valid_chunks)
    print("완료!")


if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser(description="NCS 평가 데이터셋 생성")
    parser.add_argument("--config", choices=list(_CONFIGS.keys()), required=True)
    parser.add_argument(
        "--db",
        default=os.getenv("DB_CONNECTION", "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db"),
    )
    args = parser.parse_args()

    cfg = _CONFIGS[args.config]
    asyncio.run(create_dataset(cfg, db_connection=args.db))
