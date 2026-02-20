# RAG Evaluation System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Arize Phoenix Experiments + LLM as a Judge로 RAG 버전별 품질을 자동 평가하는 `eval/` 서브패키지를 구축한다.

**Architecture:** DatasetConfig × RAGConfig 매트릭스 실험 구조. PGVector `ncs_vectors` 테이블에서 청크를 직접 SQL로 샘플링해 LLM으로 Q&A 합성 후 Phoenix Dataset으로 업로드한다. `make_task(rag_config)` 팩토리가 각 버전별 ChatAgent를 in-process로 초기화하며, `run_experiment()`가 Faithfulness / Answer Relevance / Context Relevance / Correctness 4개 지표로 버전별 성능을 비교한다.

**Tech Stack:** `arize-phoenix`, `arize-phoenix-evals`, `langchain-postgres`, `sqlalchemy[asyncio]`, `asyncpg`, `openai`, `pytest`, `pytest-asyncio`

---

## 핵심 가정 (읽어두기)

- **PGVector 테이블**: `ncs_vectors` — 컬럼 `document` (청크 텍스트), `doc_id` (VARCHAR), `page` (INTEGER)
- **카테고리 정보**: `doc_id` ↔ main/sub_category 매핑은 Oracle에 있어 평가 시 접근 불가. Dataset input에는 `doc_id`만 포함하고, task function이 해당 `doc_id`로 필터링 검색
- **비동기 처리**: `run_experiment()` task는 동기 함수. 내부에서 `asyncio.run()` 으로 async 에이전트를 래핑
- **평가 judge**: `gpt-4o` (피평가 모델 `gpt-4o-mini`보다 강력한 모델)
- **sys.path**: `ai_server/eval/` 안에서 실행할 때 `ai_server/`가 Python path에 있어야 함

---

## Task 1: eval 패키지 구조 + configs.py

**Files:**
- Create: `ai_server/eval/__init__.py`
- Create: `ai_server/eval/configs.py`
- Create: `ai_server/eval/tests/__init__.py`
- Create: `ai_server/eval/tests/test_configs.py`

---

**Step 1: 테스트 파일 작성**

`ai_server/eval/tests/test_configs.py`:
```python
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
```

---

**Step 2: 테스트 실패 확인**

```bash
cd ai_server && python -m pytest eval/tests/test_configs.py -v
```
Expected: `ModuleNotFoundError: No module named 'eval'`

---

**Step 3: `eval/__init__.py` 생성 (빈 파일)**

`ai_server/eval/__init__.py`:
```python
```

---

**Step 4: `eval/configs.py` 작성**

`ai_server/eval/configs.py`:
```python
"""
configs.py — 평가 시스템의 버전 설정 정의

DatasetConfig: 합성 데이터셋 생성 설정 (버전, 샘플 수, 생성 전략)
RAGConfig: RAG 에이전트 버전 설정 (모델, 검색 k, 프롬프트 오버라이드)
"""

from dataclasses import dataclass, field
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
```

---

**Step 5: 테스트 통과 확인**

```bash
cd ai_server && python -m pytest eval/tests/test_configs.py -v
```
Expected: 4 passed

---

**Step 6: 커밋**

```bash
git add ai_server/eval/__init__.py ai_server/eval/configs.py ai_server/eval/tests/__init__.py ai_server/eval/tests/test_configs.py
git commit -m "feat(eval): eval 패키지 구조 및 DatasetConfig/RAGConfig 정의"
```

---

## Task 2: create_dataset.py

**Files:**
- Create: `ai_server/eval/create_dataset.py`
- Create: `ai_server/eval/tests/test_create_dataset.py`

---

**PGVector 테이블 구조 (참고)**
`ncs_vectors` 테이블 컬럼: `id` (UUID), `embedding` (vector), `document` (text), `cmetadata` (jsonb), `doc_id` (VARCHAR), `page` (INTEGER)

청크 샘플링 SQL:
```sql
SELECT document, doc_id FROM ncs_vectors
WHERE doc_id IS NOT NULL
ORDER BY RANDOM()
LIMIT :num_samples
```

---

**Step 1: 테스트 파일 작성**

`ai_server/eval/tests/test_create_dataset.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

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
        MagicMock(document="청크1 내용", doc_id="uuid-001"),
        MagicMock(document="청크2 내용", doc_id="uuid-002"),
    ]
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = mock_rows

    with patch("eval.create_dataset.create_async_engine") as mock_engine_cls:
        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_chunks(db_connection="postgresql+asyncpg://test", num_samples=2)

    assert len(result) == 2
    assert result[0]["document"] == "청크1 내용"
    assert result[0]["doc_id"] == "uuid-001"


# ── build_qa_prompt 테스트 ──────────────────────────────────────

def test_build_qa_prompt_factual_contains_chunk():
    prompt = build_qa_prompt(chunk="테스트 청크 내용", strategy="factual")
    assert "테스트 청크 내용" in prompt
    assert "factual" in prompt.lower() or "사실" in prompt


def test_build_qa_prompt_reasoning_contains_chunk():
    prompt = build_qa_prompt(chunk="테스트 청크 내용", strategy="reasoning")
    assert "테스트 청크 내용" in prompt


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
```

---

**Step 2: 테스트 실패 확인**

```bash
cd ai_server && python -m pytest eval/tests/test_create_dataset.py -v
```
Expected: `ImportError: cannot import name 'fetch_chunks' from 'eval.create_dataset'`

---

**Step 3: `create_dataset.py` 작성**

`ai_server/eval/create_dataset.py`:
```python
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
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from eval.configs import DatasetConfig, DATASET_V1, DATASET_V2

logger = logging.getLogger(__name__)

_CONFIGS = {
    "v1": DATASET_V1,
    "v2": DATASET_V2,
}

_PROMPT_KEYS_IN_PROMPT = ["_PROMPT_KEYS"]  # 아래 참조

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
                f"SELECT document, doc_id FROM {TABLE_NAME} "
                "WHERE doc_id IS NOT NULL "
                "ORDER BY RANDOM() "
                "LIMIT :n"
            ),
            {"n": num_samples},
        )
    await engine.dispose()
    return [{"document": row.document, "doc_id": row.doc_id} for row in rows]


# ── Q&A 생성 ────────────────────────────────────────────────────

_FACTUAL_INSTRUCTION = (
    "문서에서 직접 찾을 수 있는 사실적인 질문을 생성하세요. "
    "답변은 문서 내용만을 근거로 작성하세요."
)

_REASONING_INSTRUCTION = (
    "문서를 읽고 추론·비교·적용이 필요한 심화 질문을 생성하세요. "
    "답변은 문서 내용을 바탕으로 논리적으로 작성하세요."
)


def build_qa_prompt(chunk: str, strategy: str) -> str:
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
    client,
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
    except (json.JSONDecodeError, KeyError):
        logger.warning("[create_dataset] Q&A 파싱 실패: %s", raw[:100])
        return None


# ── Phoenix 업로드 ───────────────────────────────────────────────

def upload_to_phoenix(
    config: DatasetConfig,
    qa_pairs: list[dict],
    chunks: list[dict],
    phoenix_endpoint: str = "http://localhost:6006",
) -> None:
    """생성된 Q&A 쌍을 Phoenix Dataset으로 업로드한다."""
    import phoenix as px

    client = px.Client(endpoint=phoenix_endpoint)
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

    dataset = client.upload_dataset(
        dataset_name=config.name,
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
```

---

**Step 4: 테스트 통과 확인**

```bash
cd ai_server && python -m pytest eval/tests/test_create_dataset.py -v
```
Expected: 6 passed

---

**Step 5: 커밋**

```bash
git add ai_server/eval/create_dataset.py ai_server/eval/tests/test_create_dataset.py
git commit -m "feat(eval): create_dataset.py — PGVector 청크 샘플링 + LLM Q&A 합성 + Phoenix 업로드"
```

---

## Task 3: tasks.py

**Files:**
- Create: `ai_server/eval/tasks.py`
- Create: `ai_server/eval/tests/test_tasks.py`

---

**맥락 이해 (중요)**

- `run_experiment()` task 함수는 **동기(sync)** 함수여야 함
- 기존 `ChatAgent.run()`은 **비동기**이므로 `asyncio.run()` 으로 래핑
- 각 task 호출마다 새 `VectorStoreManager`를 생성 (event loop 격리)
- retrieved_context는 에이전트 실행 후 `ToolMessage.content`에서 추출
- `prompt_override`가 있으면 Redis 로드 후 해당 키를 교체

---

**Step 1: 테스트 파일 작성**

`ai_server/eval/tests/test_tasks.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from eval.configs import RAGConfig, V1_BASELINE
from eval.tasks import make_task, extract_context_from_messages, build_system_prompt_with_override


# ── extract_context_from_messages 테스트 ────────────────────────

def test_extract_context_returns_tool_message_content():
    """ToolMessage가 있으면 content를 반환한다."""
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

    messages = [
        HumanMessage(content="질문"),
        AIMessage(content="", tool_calls=[]),
        ToolMessage(content="검색된 컨텍스트 내용", tool_call_id="id1"),
        AIMessage(content="최종 답변"),
    ]
    result = extract_context_from_messages(messages)
    assert result == "검색된 컨텍스트 내용"


def test_extract_context_returns_empty_when_no_tool_message():
    """ToolMessage가 없으면 빈 문자열을 반환한다."""
    from langchain_core.messages import HumanMessage, AIMessage

    messages = [HumanMessage(content="질문"), AIMessage(content="답변")]
    result = extract_context_from_messages(messages)
    assert result == ""


# ── build_system_prompt_with_override 테스트 ────────────────────

def test_build_system_prompt_override_replaces_specific_key():
    """prompt_override의 특정 키가 Redis 값 대신 사용된다."""
    mock_get_prompt = MagicMock(return_value="redis_value")
    override = {"agent_system_prompt": "custom_system_prompt"}

    with patch("eval.tasks.get_prompt", mock_get_prompt):
        result = build_system_prompt_with_override(override)

    assert "custom_system_prompt" in result
    # 오버라이드되지 않은 키는 redis_value 사용
    assert "redis_value" in result


def test_build_system_prompt_override_skips_empty_parts():
    """빈 문자열 프롬프트는 결합에서 제외된다."""
    def mock_get_prompt(key):
        return "" if key == "category_hint_prompt" else "value"

    override = {}
    with patch("eval.tasks.get_prompt", mock_get_prompt):
        result = build_system_prompt_with_override(override)

    assert "value" in result


# ── make_task 팩토리 테스트 ─────────────────────────────────────

def test_make_task_returns_callable():
    task = make_task(V1_BASELINE, db_connection="postgresql+asyncpg://test")
    assert callable(task)


def test_make_task_output_has_required_keys():
    """task 함수가 answer와 retrieved_context를 반환한다."""
    from langchain_core.messages import AIMessage, ToolMessage

    mock_last_message = AIMessage(content="에이전트 최종 답변")
    mock_messages = [
        ToolMessage(content="검색된 컨텍스트", tool_call_id="id1"),
        mock_last_message,
    ]
    mock_event = {"messages": mock_messages}

    async def mock_astream(*args, **kwargs):
        yield mock_event

    with patch("eval.tasks.VectorStoreManager") as mock_vsm_cls, \
         patch("eval.tasks.EmbeddingModel") as mock_emb_cls, \
         patch("eval.tasks.ToolBuilder") as mock_tb_cls, \
         patch("eval.tasks.ChatAgent") as mock_agent_cls:

        mock_vsm = AsyncMock()
        mock_vsm_cls.create = AsyncMock(return_value=mock_vsm)
        mock_emb_cls.return_value.get_embeddings.return_value = MagicMock()
        mock_tb_cls.return_value.build_tools.return_value = []

        mock_agent_instance = MagicMock()
        mock_agent_instance.agent.astream = mock_astream
        mock_agent_cls.return_value = mock_agent_instance

        task = make_task(V1_BASELINE, db_connection="postgresql+asyncpg://test")
        example = {"input": {"question": "테스트 질문", "doc_id": "uuid-001"}}
        result = task(example)

    assert "answer" in result
    assert "retrieved_context" in result
    assert result["answer"] == "에이전트 최종 답변"
    assert result["retrieved_context"] == "검색된 컨텍스트"
```

---

**Step 2: 테스트 실패 확인**

```bash
cd ai_server && python -m pytest eval/tests/test_tasks.py -v
```
Expected: `ImportError: cannot import name 'make_task' from 'eval.tasks'`

---

**Step 3: `tasks.py` 작성**

`ai_server/eval/tasks.py`:
```python
"""
tasks.py — run_experiment() 용 task function 팩토리

make_task(rag_config, db_connection) → 동기 task 함수 반환
task 함수 시그니처: (example: dict) -> {"answer": str, "retrieved_context": str}

example 구조:
  example["input"]["question"] : 질문 텍스트
  example["input"]["doc_id"]   : 검색 필터용 doc_id
"""

import asyncio
import os
from typing import Optional

from langchain_core.messages import ToolMessage

from agent import ChatAgent
from embeddings import EmbeddingModel
from tool import ToolBuilder
from vector_store import VectorStoreManager
from prompt_loader import get_prompt
from eval.configs import RAGConfig

_PROMPT_KEYS = [
    "agent_system_prompt",
    "answer_format_prompt",
    "no_document_prompt",
    "query_enhance_prompt",
    "category_hint_prompt",
]


def extract_context_from_messages(messages: list) -> str:
    """에이전트 메시지 목록에서 첫 번째 ToolMessage content를 반환한다."""
    for msg in messages:
        if isinstance(msg, ToolMessage):
            return msg.content or ""
    return ""


def build_system_prompt_with_override(prompt_override: dict) -> str:
    """Redis에서 프롬프트를 로드하되 override 딕셔너리의 키로 교체한다."""
    parts = []
    for key in _PROMPT_KEYS:
        if key in prompt_override:
            p = prompt_override[key]
        else:
            p = get_prompt(key)
        if p:
            parts.append(p)
    return "\n\n".join(parts)


def make_task(rag_config: RAGConfig, db_connection: str):
    """RAGConfig 기반으로 task function을 생성한다.

    반환된 task 함수는 run_experiment()에 직접 전달할 수 있다.
    각 호출마다 새로운 VectorStoreManager와 ChatAgent를 초기화한다.
    """

    def task(example: dict) -> dict:
        question = example["input"]["question"]
        doc_id: Optional[str] = example["input"].get("doc_id")

        async def _run():
            embedding_model = EmbeddingModel().get_embeddings()
            vsm = await VectorStoreManager.create(
                connection_string=db_connection,
                embedding_model=embedding_model,
            )

            tool_builder = ToolBuilder(vsm)
            tools = tool_builder.build_tools(
                doc_ids=[doc_id] if doc_id else None,
                k=rag_config.retrieval_k,
            )

            if rag_config.prompt_override is not None:
                system_prompt = build_system_prompt_with_override(rag_config.prompt_override)
            else:
                system_prompt = None  # ChatAgent가 Redis에서 로드

            agent = ChatAgent(
                model_name=rag_config.model_name,
                system_prompt=system_prompt,
            )
            agent.create_agent(tools)

            final_messages = []
            async for event in agent.agent.astream(
                {"messages": [{"role": "user", "content": question}]},
                stream_mode="values",
            ):
                final_messages = event["messages"]

            answer = final_messages[-1].content if final_messages else ""
            retrieved_context = extract_context_from_messages(final_messages)

            return {"answer": answer, "retrieved_context": retrieved_context}

        return asyncio.run(_run())

    return task
```

> **주의**: `ToolBuilder.build_tools()`에 `k` 파라미터를 추가해야 한다 (Task 3 Step 4 참조).

---

**Step 4: `tool.py` 수정 — `build_tools()`에 `k` 파라미터 추가**

`ai_server/tool.py` 의 `build_tools` 시그니처를 수정:

```python
# 수정 전
def build_tools(self, doc_ids: Optional[List[str]] = None) -> List[Tool]:

# 수정 후
def build_tools(self, doc_ids: Optional[List[str]] = None, k: int = 4) -> List[Tool]:
```

내부 `similarity_search_by_doc_ids` 호출의 `k=4` 하드코딩도 `k=k`로 변경:
```python
# 수정 전
retrieved_docs = await vsm.similarity_search_by_doc_ids(query, doc_ids=_doc_ids, k=4)

# 수정 후
retrieved_docs = await vsm.similarity_search_by_doc_ids(query, doc_ids=_doc_ids, k=_k)
```

그리고 클로저 앞에 `_k = k` 추가:
```python
def build_tools(self, doc_ids: Optional[List[str]] = None, k: int = 4) -> List[Tool]:
    vsm = self.vsm
    _doc_ids = doc_ids or []
    _k = k

    @tool(response_format="content_and_artifact")
    async def retrieve_context(query: str):
        retrieved_docs = await vsm.similarity_search_by_doc_ids(
            query, doc_ids=_doc_ids, k=_k
        )
        ...
```

---

**Step 5: 테스트 통과 확인**

```bash
cd ai_server && python -m pytest eval/tests/test_tasks.py -v
```
Expected: 6 passed

---

**Step 6: 커밋**

```bash
git add ai_server/eval/tasks.py ai_server/eval/tests/test_tasks.py ai_server/tool.py
git commit -m "feat(eval): tasks.py — make_task 팩토리 + tool.py k 파라미터 추가"
```

---

## Task 4: evaluators.py

**Files:**
- Create: `ai_server/eval/evaluators.py`
- Create: `ai_server/eval/tests/test_evaluators.py`

---

**맥락 이해**

`run_experiment()` evaluator 시그니처: `(input: dict, output: dict, expected: dict) -> float`
- `input` = dataset의 `input` 필드 (`{question, doc_id}`)
- `output` = task의 반환값 (`{answer, retrieved_context}`)
- `expected` = dataset의 `output` 필드 (`{reference_answer}`)

Phoenix built-in evaluator (`run_evals`)는 별도의 단일 행 DataFrame을 구성해 호출한다.

---

**Step 1: 테스트 파일 작성**

`ai_server/eval/tests/test_evaluators.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

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


# ── Faithfulness 테스트 ──────────────────────────────────────────

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


# ── Correctness 테스트 ───────────────────────────────────────────

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


# ── Answer Relevance 테스트 ─────────────────────────────────────

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


# ── create_all_evaluators 테스트 ─────────────────────────────────

def test_create_all_evaluators_returns_four():
    judge_model = _make_judge_model()
    evaluators = create_all_evaluators(judge_model)
    assert len(evaluators) == 4
    for ev in evaluators:
        assert callable(ev)
```

---

**Step 2: 테스트 실패 확인**

```bash
cd ai_server && python -m pytest eval/tests/test_evaluators.py -v
```
Expected: `ImportError`

---

**Step 3: `evaluators.py` 작성**

`ai_server/eval/evaluators.py`:
```python
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
```

---

**Step 4: 테스트 통과 확인**

```bash
cd ai_server && python -m pytest eval/tests/test_evaluators.py -v
```
Expected: 7 passed

---

**Step 5: 커밋**

```bash
git add ai_server/eval/evaluators.py ai_server/eval/tests/test_evaluators.py
git commit -m "feat(eval): evaluators.py — Faithfulness/ContextRel/Correctness/AnswerRel 4개 지표"
```

---

## Task 5: run_evaluation.py

**Files:**
- Create: `ai_server/eval/run_evaluation.py`
- Create: `ai_server/eval/tests/test_run_evaluation.py`

---

**Step 1: 테스트 파일 작성**

`ai_server/eval/tests/test_run_evaluation.py`:
```python
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
```

---

**Step 2: 테스트 실패 확인**

```bash
cd ai_server && python -m pytest eval/tests/test_run_evaluation.py -v
```
Expected: `ImportError`

---

**Step 3: `run_evaluation.py` 작성**

`ai_server/eval/run_evaluation.py`:
```python
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
        dataset = phoenix_client.get_dataset(name=dataset_config.name)
        logger.info("[eval] 기존 데이터셋 로드: %s", dataset_config.name)
        return dataset
    except Exception:
        logger.info("[eval] 데이터셋 없음. 생성 시작: %s", dataset_config.name)
        asyncio.run(create_dataset(dataset_config, db_connection=db_connection))
        return phoenix_client.get_dataset(name=dataset_config.name)


def run_all(
    dataset_keys: list[str],
    agent_keys: list[str],
    db_connection: str,
    phoenix_endpoint: str = "http://localhost:6006",
    judge_model_name: str = "gpt-4o",
):
    """지정된 조합으로 전체 실험을 실행한다."""
    import phoenix as px
    from phoenix.evals import OpenAIModel
    from phoenix.experiments import run_experiment

    dataset_configs = [_DATASET_REGISTRY[k] for k in dataset_keys]
    rag_configs = [_AGENT_REGISTRY[k] for k in agent_keys]
    matrix = build_experiment_matrix(dataset_configs, rag_configs)

    print(f"\n실험 매트릭스: {len(matrix)}개 조합")
    for name, _, _ in matrix:
        print(f"  - {name}")
    print()

    phoenix_client = px.Client(endpoint=phoenix_endpoint)
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
```

---

**Step 4: 테스트 통과 확인**

```bash
cd ai_server && python -m pytest eval/tests/test_run_evaluation.py -v
```
Expected: 4 passed

---

**Step 5: 전체 테스트 스위트 통과 확인**

```bash
cd ai_server && python -m pytest eval/tests/ -v
```
Expected: 모든 테스트 통과

---

**Step 6: 커밋**

```bash
git add ai_server/eval/run_evaluation.py ai_server/eval/tests/test_run_evaluation.py
git commit -m "feat(eval): run_evaluation.py — 실험 매트릭스 실행 진입점"
```

---

## Task 6: 패키지 의존성 추가

**Files:**
- Modify: `ai_server/requirements.txt` (또는 존재하는 의존성 파일)

---

**Step 1: 의존성 파일 확인**

```bash
ls ai_server/
```

`requirements.txt`가 없으면 생성. 있으면 아래 항목 추가:

```
arize-phoenix-evals
pytest-asyncio
```

**Step 2: 설치 확인**

```bash
pip install arize-phoenix-evals pytest-asyncio
python -c "from phoenix.evals import HallucinationEvaluator; print('OK')"
```

**Step 3: 전체 테스트 재실행**

```bash
cd ai_server && python -m pytest eval/tests/ -v
```
Expected: 전체 통과

**Step 4: 커밋**

```bash
git add ai_server/requirements.txt  # 또는 변경된 파일
git commit -m "chore(eval): arize-phoenix-evals, pytest-asyncio 의존성 추가"
```

---

## 통합 검증 (선택, 실제 서비스 가동 필요)

```bash
# 1. Phoenix 실행 확인
curl http://localhost:6006/health

# 2. 소규모 데이터셋 생성 테스트 (10개)
cd ai_server
python -c "
from eval.configs import DatasetConfig
import asyncio
from eval.create_dataset import create_dataset
cfg = DatasetConfig('ncs-rag-eval-smoke', 'smoke', 10, 'factual', None)
asyncio.run(create_dataset(cfg, 'postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db'))
"

# 3. 단일 실험 실행 (v1 베이스라인만)
python -m eval.run_evaluation --datasets v1 --agents v1_baseline
```

---

## 개발 순서 요약

| Task | 핵심 파일 | 예상 소요 |
|---|---|---|
| 1 | `eval/__init__.py`, `configs.py` | 10분 |
| 2 | `create_dataset.py` | 30분 |
| 3 | `tasks.py` + `tool.py` 수정 | 30분 |
| 4 | `evaluators.py` | 20분 |
| 5 | `run_evaluation.py` | 20분 |
| 6 | 의존성 추가 | 5분 |
