# RAG 평가 시스템 아키텍처

> `ai_server/eval/` 모듈의 동작 원리를 상세히 설명한다.

---

## 목차

1. [전체 구조 개요](#1-전체-구조-개요)
2. [데이터 흐름](#2-데이터-흐름)
3. [모듈별 상세 설명](#3-모듈별-상세-설명)
   - [configs.py](#31-configspy)
   - [create_dataset.py](#32-create_datasetpy)
   - [tasks.py](#33-taskspy)
   - [evaluators.py](#34-evaluatorspy)
   - [run_evaluation.py](#35-run_evaluationpy)
4. [평가 지표 정의](#4-평가-지표-정의)
5. [실험 매트릭스](#5-실험-매트릭스)
6. [새 RAG 버전 추가 방법](#6-새-rag-버전-추가-방법)

---

## 1. 전체 구조 개요

```
eval/
├── configs.py          # DatasetConfig / RAGConfig 버전 정의
├── create_dataset.py   # PGVector 샘플링 → LLM Q&A 합성 → Phoenix 업로드
├── tasks.py            # RAG 파이프라인을 Phoenix task function으로 래핑
├── evaluators.py       # 4개 평가 지표 함수 (faithfulness, context_relevance, correctness, answer_relevance)
├── run_evaluation.py   # 실험 매트릭스 구성 + phoenix.experiments.run_experiment() 실행
└── tests/              # pytest 단위 테스트 (30개)
```

**외부 의존 서비스:**

| 서비스 | 역할 | 기본 주소 |
|---|---|---|
| PostgreSQL + pgvector | NCS 문서 청크 저장 / 벡터 검색 | localhost:5432/pdf_db |
| Redis | 시스템 프롬프트 로드 (없으면 fallback) | localhost:6379 |
| Arize Phoenix | 데이터셋 저장 / 실험 결과 시각화 | localhost:6006 |
| OpenAI API | Q&A 합성 LLM / 평가 judge LLM / embedding | api.openai.com |

---

## 2. 데이터 흐름

```
[Phase 1] 데이터셋 생성 (create_dataset.py)
─────────────────────────────────────────────────────────────────────
  PGVector(ncs_vectors)
      │  SELECT content, doc_id RANDOM LIMIT n
      ▼
  청크 목록 [{document, doc_id}, ...]
      │  build_qa_prompt(chunk, strategy)
      │  OpenAI gpt-4o → JSON {"question", "reference_answer"}
      ▼
  Q&A 쌍 목록 [{question, reference_answer}, ...]
      │  phoenix.client.Client.datasets.create_dataset()
      ▼
  Phoenix Dataset
    inputs:   [{question, doc_id}, ...]
    outputs:  [{reference_answer}, ...]
    metadata: [{source_chunk, strategy, version}, ...]


[Phase 2] 실험 실행 (run_evaluation.py + tasks.py + evaluators.py)
─────────────────────────────────────────────────────────────────────
  Phoenix Dataset
      │  run_experiment(dataset, task=task_fn, evaluators=[...])
      │
      │  ┌── 각 Example에 대해 병렬 실행 ─────────────────────┐
      │  │                                                      │
      │  │  [task_fn(example)]                                  │
      │  │    example.input["question"]                         │
      │  │    example.input["doc_id"]                           │
      │  │         │                                            │
      │  │    EmbeddingModel → VectorStoreManager               │
      │  │    ToolBuilder.build_tools(doc_ids=[doc_id], k=K)    │
      │  │    ChatAgent(model, system_prompt)                   │
      │  │    agent.astream({"messages": [question]})           │
      │  │         │                                            │
      │  │    → {"answer": str, "retrieved_context": str}       │
      │  │                                                      │
      │  │  [evaluator_fn(input, output, expected)]             │
      │  │    faithfulness    → HallucinationEvaluator          │
      │  │    context_relevance → RelevanceEvaluator            │
      │  │    correctness     → QAEvaluator                     │
      │  │    answer_relevance → llm_classify (custom)          │
      │  │         │                                            │
      │  │    → score: 0.0 또는 1.0                             │
      │  └──────────────────────────────────────────────────────┘
      │
      ▼
  Phoenix UI (localhost:6006)
    실험명, 평균 점수, 예시별 결과, 지표별 히스토그램
```

---

## 3. 모듈별 상세 설명

### 3.1 `configs.py`

모든 버전 설정을 상수로 정의한다. 코드 변경 없이 설정만 추가하면 새 실험을 등록할 수 있다.

#### `DatasetConfig`

```python
@dataclass
class DatasetConfig:
    name: str               # Phoenix 데이터셋 이름 (고유 식별자)
    version: str            # 버전 레이블
    num_samples: int        # 생성할 Q&A 쌍 수
    generation_strategy: Literal["factual", "reasoning", "mixed"]
```

| `generation_strategy` | 설명 |
|---|---|
| `factual` | 문서에서 직접 찾을 수 있는 사실 기반 질문 |
| `reasoning` | 추론·비교·적용이 필요한 심화 질문 |
| `mixed` | 각 청크마다 factual / reasoning 중 무작위 선택 |

현재 정의된 데이터셋:

| 상수 | name | num_samples | strategy |
|---|---|---|---|
| `DATASET_V1` | ncs-rag-eval-v1 | 50 | factual |
| `DATASET_V2` | ncs-rag-eval-v2 | 100 | mixed |

#### `RAGConfig`

```python
@dataclass
class RAGConfig:
    version: str                    # 실험 이름에 사용되는 버전 레이블
    model_name: str                 # OpenAI 모델명
    retrieval_k: int                # 벡터 검색 top-k
    prompt_override: Optional[dict] # None → Redis 로드 / dict → 키별 오버라이드
```

현재 정의된 RAG 버전:

| 상수 | model | k | prompt |
|---|---|---|---|
| `V1_BASELINE` | gpt-4o-mini | 4 | Redis(fallback) |
| `V2_GPT4O` | gpt-4o | 4 | Redis(fallback) |
| `V3_K8` | gpt-4o-mini | 8 | Redis(fallback) |

---

### 3.2 `create_dataset.py`

평가용 Q&A 데이터셋을 합성해서 Phoenix에 업로드하는 파이프라인이다.

#### 실행 흐름

**Step 1: PGVector 청크 샘플링 (`fetch_chunks`)**

```sql
SELECT content, doc_id
FROM ncs_vectors
WHERE doc_id IS NOT NULL
ORDER BY RANDOM()
LIMIT :n
```

- `ncs_vectors` 테이블의 실제 컬럼명은 `content` (langchain_postgres 기본 스키마)
- `doc_id`로 필터링해 특정 문서 ID를 추적 가능하게 유지
- SQLAlchemy async engine으로 비동기 실행

**Step 2: LLM Q&A 합성 (`generate_qa_pair`)**

각 청크에 대해 아래 프롬프트를 OpenAI에 전송한다:

```
당신은 NCS 교육 평가 전문가입니다.
아래 문서 청크를 읽고 질문-답변 쌍을 1개 생성하세요.

지침: {factual 또는 reasoning 지침}

[문서 청크]
{chunk_text}

반드시 아래 JSON 형식으로만 응답하세요:
{"question": "...", "reference_answer": "..."}
```

- `response_format={"type": "json_object"}` 로 JSON 응답 강제
- 파싱 실패 시 해당 청크는 건너뛰고 `None` 반환

**Step 3: Phoenix 업로드 (`upload_to_phoenix`)**

```python
client.datasets.create_dataset(
    name=config.name,
    inputs=[{"question": ..., "doc_id": ...}],     # task가 받는 값
    outputs=[{"reference_answer": ...}],            # evaluator가 expected로 받는 값
    metadata=[{"source_chunk", "strategy", "version"}]
)
```

Phoenix Dataset의 각 row(Example)는 다음 구조를 갖는다:

```
Example
├── input    = {"question": "...", "doc_id": "uuid-..."}
├── output   = {"reference_answer": "..."}
└── metadata = {"source_chunk": "...", "generation_strategy": "...", "dataset_version": "..."}
```

---

### 3.3 `tasks.py`

Phoenix `run_experiment()`에 전달할 task function을 생성하는 팩토리 모듈이다.

#### `make_task(rag_config, db_connection) → task_fn`

task function은 Phoenix가 각 Example에 대해 호출한다:

```python
def task(example) -> dict:
    question = example.input["question"]      # Phoenix Example 객체는 .input 속성 사용
    doc_id   = example.input.get("doc_id")
    ...
    return {"answer": ..., "retrieved_context": ...}
```

> **주의:** Phoenix `run_experiment()`가 넘기는 `example`은 일반 dict가 아니라
> `phoenix.experiments.types.Example` 객체다. `example["input"]`이 아닌
> `example.input`으로 접근해야 한다.

#### 내부 RAG 파이프라인 (`_run`)

```
EmbeddingModel()
    → VectorStoreManager.create(db_connection, embedding_model)
    → ToolBuilder.build_tools(doc_ids=[doc_id], k=rag_config.retrieval_k)
    → ChatAgent(model_name, system_prompt)
    → agent.astream({"messages": [{"role": "user", "content": question}]})
    → 마지막 AIMessage.content = answer
    → 첫 번째 ToolMessage.content = retrieved_context
```

- `doc_id`가 있으면 해당 문서 내에서만 검색하도록 필터 적용
- `system_prompt`: `rag_config.prompt_override`가 None이면 Redis에서 로드, dict면 지정된 키만 오버라이드
- Redis 연결 실패 시 `prompt_loader.py`의 fallback 프롬프트 사용 (평가 영향 없음)

#### asyncio 이벤트 루프 처리

Phoenix `run_experiment()`는 내부적으로 스레드 풀에서 task를 실행한다. 이미 실행 중인 이벤트 루프가 있으면 `asyncio.run()`을 직접 호출할 수 없다.

```python
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = None

if loop is not None and loop.is_running():
    # 별도 스레드에서 새 이벤트 루프 생성
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, _run()).result()
return asyncio.run(_run())
```

---

### 3.4 `evaluators.py`

4개의 평가 지표를 정의한다. 각 지표는 `(input, output, expected) → float` 시그니처를 따른다.

#### 인자 매핑

| 인자 | 출처 | 내용 |
|---|---|---|
| `input` | Dataset `inputs` | `{"question": str, "doc_id": str}` |
| `output` | task 반환값 | `{"answer": str, "retrieved_context": str}` |
| `expected` | Dataset `outputs` | `{"reference_answer": str}` |

#### 4개 지표 상세

**① Faithfulness (환각 탐지)**

```
질문: input["question"]
답변: output["answer"]
컨텍스트: output["retrieved_context"]  ← 검색된 실제 문서 내용
```

- `HallucinationEvaluator` 사용
- judge LLM이 "답변이 컨텍스트에 근거하는가"를 판단
- 1.0 = 근거 있음 (faithful), 0.0 = 환각 (hallucinated)

**② Context Relevance (검색 품질)**

```
질문: input["question"]
컨텍스트: output["retrieved_context"]
```

- `RelevanceEvaluator` 사용
- judge LLM이 "검색된 문서가 질문과 관련 있는가"를 판단
- 1.0 = 관련 있음, 0.0 = 무관

**③ Correctness (정답 일치도)**

```
질문: input["question"]
답변: output["answer"]
정답: expected["reference_answer"]  ← 데이터셋 생성 시 LLM이 합성한 기준 답변
```

- `QAEvaluator` 사용
- judge LLM이 "답변이 reference_answer와 일치하는가"를 판단
- 1.0 = 일치, 0.0 = 불일치

**④ Answer Relevance (답변 관련성, 커스텀)**

```
질문: input["question"]
답변: output["answer"]
```

- `llm_classify` + 커스텀 한국어 프롬프트 사용
- reference_answer를 사용하지 않고 질문-답변 직접 비교
- rails: `["relevant", "irrelevant"]`
- 1.0 = relevant, 0.0 = irrelevant

#### judge LLM

기본값은 `gpt-4o`, `temperature=0.0`으로 고정해 평가 재현성을 보장한다.

```bash
python -m eval.run_evaluation --judge gpt-4o-mini  # 비용 절감 시 변경 가능
```

---

### 3.5 `run_evaluation.py`

전체 실험의 진입점이다.

#### `build_experiment_matrix`

`DatasetConfig × RAGConfig`의 카르테시안 곱으로 실험 목록을 생성한다.

```python
# 예: datasets=[v1, v2], agents=[baseline, gpt4o]
# → 4개 실험:
#   "v1_baseline_on_ncs-rag-eval-v1"
#   "v2_gpt4o_on_ncs-rag-eval-v1"
#   "v1_baseline_on_ncs-rag-eval-v2"
#   "v2_gpt4o_on_ncs-rag-eval-v2"
```

실험명 형식: `{rag_config.version}_on_{dataset_config.name}`

#### `get_or_create_dataset`

Phoenix에 데이터셋이 이미 있으면 그대로 사용하고, 없으면 `create_dataset()`을 실행해 새로 생성한다. 동일한 데이터셋으로 여러 RAG 버전을 비교할 때 중복 생성을 방지한다.

```python
try:
    return phoenix_client.datasets.get_dataset(dataset=config.name)
except Exception:
    asyncio.run(create_dataset(config, db_connection))
    return phoenix_client.datasets.get_dataset(dataset=config.name)
```

#### `run_all` 실행 흐름

```
1. CLI args 파싱 (--datasets, --agents, --db, --phoenix, --judge)
2. 실험 매트릭스 구성
3. Phoenix Client 초기화
4. OpenAI judge 모델 초기화 (gpt-4o, temperature=0)
5. 4개 evaluator 생성

for 각 실험:
    6. get_or_create_dataset() → Phoenix Dataset 객체
    7. make_task(rag_config, db_connection) → task function
    8. run_experiment(dataset, task, evaluators, experiment_name)
    9. 결과는 Phoenix UI에 자동 저장
```

---

## 4. 평가 지표 정의

| 지표 | 비교 대상 | 측정 내용 | 높을수록 |
|---|---|---|---|
| **Faithfulness** | answer ↔ retrieved_context | 답변이 검색 문서에 근거하는가 | 환각 없음 |
| **Context Relevance** | question ↔ retrieved_context | 검색 문서가 질문과 관련 있는가 | 검색 정확도 높음 |
| **Correctness** | answer ↔ reference_answer | 답변이 정답과 일치하는가 | 정답 재현율 높음 |
| **Answer Relevance** | question ↔ answer | 답변이 질문에 직접 답하는가 | 답변 적절성 높음 |

**Faithfulness vs Correctness 차이:**

- `Faithfulness`: "답변이 검색된 문서에서 나온 말인가?" → RAG 검색 품질 평가
- `Correctness`: "답변이 사전에 준비된 정답과 같은가?" → 절대적 정확도 평가

---

## 5. 실험 매트릭스

현재 정의된 조합으로 최대 6개 실험이 가능하다:

```
datasets: [DATASET_V1, DATASET_V2]
agents:   [V1_BASELINE, V2_GPT4O, V3_K8]

┌─────────────────┬──────────────────────────────┬──────────────────────────────┐
│                 │      ncs-rag-eval-v1          │      ncs-rag-eval-v2          │
│                 │  (50개, factual)              │  (100개, mixed)               │
├─────────────────┼──────────────────────────────┼──────────────────────────────┤
│ v1_baseline     │ v1_baseline_on_ncs-rag-eval-v1│ v1_baseline_on_ncs-rag-eval-v2│
│ gpt-4o-mini k=4 │                              │                              │
├─────────────────┼──────────────────────────────┼──────────────────────────────┤
│ v2_gpt4o        │ v2_gpt4o_on_ncs-rag-eval-v1  │ v2_gpt4o_on_ncs-rag-eval-v2  │
│ gpt-4o k=4      │                              │                              │
├─────────────────┼──────────────────────────────┼──────────────────────────────┤
│ v3_k8           │ v3_k8_on_ncs-rag-eval-v1     │ v3_k8_on_ncs-rag-eval-v2     │
│ gpt-4o-mini k=8 │                              │                              │
└─────────────────┴──────────────────────────────┴──────────────────────────────┘
```

---

## 6. 새 RAG 버전 추가 방법

`configs.py`에 `RAGConfig` 상수를 추가하고 레지스트리에 등록한다.

**Step 1: `eval/configs.py`에 설정 추가**

```python
V4_CUSTOM_PROMPT = RAGConfig(
    version="v4_custom_prompt",
    model_name="gpt-4o-mini",
    retrieval_k=4,
    prompt_override={
        "agent_system_prompt": "커스텀 시스템 프롬프트 내용...",
    },
)
```

**Step 2: `eval/run_evaluation.py` 레지스트리에 등록**

```python
_AGENT_REGISTRY = {
    "v1_baseline": V1_BASELINE,
    "v2_gpt4o":    V2_GPT4O,
    "v3_k8":       V3_K8,
    "v4_custom":   V4_CUSTOM_PROMPT,   # 추가
}
```

**Step 3: 실행**

```bash
cd ai_server
python -m eval.run_evaluation --datasets v1 --agents v4_custom
```

결과는 Phoenix UI(`http://localhost:6006`)에서 기존 버전과 나란히 비교 가능하다.
