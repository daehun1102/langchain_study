# NCS RAG Chatbot — 평가 시스템 설계

**작성일:** 2026-02-20
**상태:** 승인됨

---

## 1. 배경 및 목표

현재 NCS RAG Chatbot은 Arize Phoenix로 트레이싱 중이나 품질 평가는 수행하지 않고 있다.
이 설계는 다음을 목표로 한다:

- **버전별 RAG 평가**: 모델, 프롬프트, 검색 파라미터, 에이전트 구조 등 변경사항을 체계적으로 비교
- **LLM as a Judge**: Arize Phoenix의 내장 평가기 + 커스텀 평가기로 4개 지표 자동 평가
- **합성 데이터셋 구축**: NCS PDF 청크를 기반으로 LLM이 Q&A 쌍 생성
- **실험 매트릭스**: (RAG 버전) × (Dataset 버전) 조합으로 Phoenix UI에서 side-by-side 비교

---

## 2. 전체 아키텍처

### 핵심 개념: (Agent 버전) × (Dataset 버전) 매트릭스

```
                dataset-v1(소규모·단순)  dataset-v2(중규모·추론형)
agent-v1(기준)       실험 A               실험 B
agent-v2(gpt-4o)     실험 C               실험 D
agent-v3(k=8)        실험 E               실험 F
```

Phoenix UI에서 같은 데이터셋 기준으로 agent 버전 비교, 또는 같은 agent 기준으로 데이터셋 난이도별 성능 확인 가능.

### 전체 흐름

```
[DatasetConfig]                    [RAGConfig]
  name, num_samples,                 version, model_name,
  generation_strategy,               retrieval_k,
  categories                         prompt_override
       ↓                                  ↓
[create_dataset.py]            [tasks.py + configs.py]
  PGVector chunks 샘플링           ChatAgent 초기화 팩토리
  LLM Q&A 합성                     task function 생성
  Phoenix Dataset 업로드
       ↓                                  ↓
            [run_evaluation.py]
            run_experiment(
              dataset    = get_dataset(dataset_config.name),
              task       = make_task(rag_config),
              evaluators = [Faithfulness, AnswerRelevance, ContextRelevance, Correctness],
              experiment_name = f"{rag_config.version}_on_{dataset_config.name}"
            )
                      ↓
              Phoenix UI — 버전별 비교 대시보드
```

### 디렉토리 구조

```
ai_server/
├── agent.py          (기존)
├── tool.py           (기존)
├── tracing.py        (기존)
└── eval/
    ├── __init__.py
    ├── configs.py           # DatasetConfig + RAGConfig 정의
    ├── create_dataset.py    # PGVector → LLM Q&A 합성 → Phoenix Dataset 업로드
    ├── tasks.py             # make_task(rag_config) 팩토리
    ├── evaluators.py        # 4개 평가 지표 정의
    └── run_evaluation.py    # 실험 실행 진입점 (매트릭스 조합)
```

---

## 3. Dataset 구축 설계

### DatasetConfig

```python
@dataclass
class DatasetConfig:
    name: str                    # Phoenix dataset 이름 ("ncs-rag-eval-v1")
    version: str                 # "v1", "v2", ...
    num_samples: int             # 생성할 Q&A 쌍 총 개수
    generation_strategy: str     # "factual" | "reasoning" | "mixed"
    categories: list[str] | None # None = 전체, 특정 카테고리만 필터링 가능
```

### Phoenix Dataset 레코드 구조

```
input:    { question, main_category, sub_category }
output:   { reference_answer }        ← LLM이 생성한 정답 (Correctness 평가 기준)
metadata: { source_chunk, doc_id,
            generation_strategy, dataset_version }
```

### create_dataset.py 실행 흐름

```
PGVector ncs_vectors 테이블
        ↓ (SQLAlchemy 직접 쿼리 — 전체 청크 수집용)
전체 청크 로드 (doc_id, content, main_category, sub_category)
        ↓
DatasetConfig.categories 필터 적용 (None이면 전체)
        ↓
num_samples 개수만큼 청크 랜덤 샘플링 (ORDER BY RANDOM())
        ↓
각 청크 → LLM 호출 (generation_strategy 별 프롬프트)
        ↓
Q&A 파싱 실패 건 제거
        ↓
px.Client().upload_dataset(name=config.name, inputs=..., outputs=..., metadata=...)
```

**청크 소스로 직접 SQL 쿼리를 사용하는 이유**: 현재 `VectorStoreManager`는 유사도 검색만 지원하므로, 랜덤 샘플링을 위해 `ncs_vectors` 테이블에 SQLAlchemy로 직접 쿼리한다.

### generation_strategy 별 프롬프트 방향

| 전략 | 질문 유형 | 예시 |
|---|---|---|
| `factual` | 문서에서 직접 찾을 수 있는 사실 | "테스트 기획의 5단계는 무엇인가?" |
| `reasoning` | 추론·비교·적용이 필요한 질문 | "테스트 기획과 테스트 진단의 차이점은?" |
| `mixed` | factual 50% + reasoning 50% | 두 유형 혼합 |

### 초기 DatasetConfig 예시

```python
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
```

---

## 4. Agent 버전 관리 설계

### RAGConfig

```python
@dataclass
class RAGConfig:
    version: str                      # "v1_baseline", "v2_gpt4o", "v3_k8", ...
    model_name: str                   # "gpt-4o-mini", "gpt-4o", ...
    retrieval_k: int                  # similarity search top-k (기본 4)
    prompt_override: dict[str, str] | None
    # None          = Redis에서 기존 5개 프롬프트 로드
    # {"key": "..."} = 특정 키만 오버라이드, 나머지는 Redis에서 로드
```

### 초기 RAGConfig 예시

```python
V1_BASELINE = RAGConfig(
    version="v1_baseline",
    model_name="gpt-4o-mini",
    retrieval_k=4,
    prompt_override=None,        # Redis 기존 프롬프트 그대로
)

V2_GPT4O = RAGConfig(
    version="v2_gpt4o",
    model_name="gpt-4o",         # 모델만 교체
    retrieval_k=4,
    prompt_override=None,
)

V3_K8 = RAGConfig(
    version="v3_k8",
    model_name="gpt-4o-mini",
    retrieval_k=8,               # 검색 범위 확장
    prompt_override=None,
)
```

### Task Function 팩토리 (`tasks.py`)

`run_experiment()`는 `(example: dict) → output` 형태의 task를 요구한다. 버전별 설정을 클로저로 캡처하는 팩토리 패턴을 사용한다.

```
make_task(rag_config)
    ↓
RAGConfig 기반으로 ChatAgent + ToolBuilder 초기화
    ↓
반환: async def task(example) 함수
        - example["input"]["question"] 추출
        - example["input"]["main_category"] / "sub_category"로 doc_ids 조회
        - agent.run(question) 실행
        - 반환: { "answer": str, "retrieved_context": str }
```

**`VectorStoreManager`는 공유 가능** (읽기 전용 PGVector 연결). **`ChatAgent`는 실행마다 새로 초기화** (버전 간 상태 오염 방지).

---

## 5. 평가 지표 4개 설계

### 사용할 Phoenix 컴포넌트

- **Built-in 3개**: `HallucinationEvaluator`, `QAEvaluator`, `RelevanceEvaluator`
- **Custom 1개**: Answer Relevance — `llm_classify`로 직접 구현

### 4개 지표 정의

| 지표 | Phoenix 구현 | 입력 | 레이블 | 점수 |
|---|---|---|---|---|
| **Faithfulness** | `HallucinationEvaluator` | answer + retrieved_context | factual / hallucinated | 1 / 0 |
| **Answer Relevance** | `llm_classify` (custom) | question + answer | relevant / irrelevant | 1 / 0 |
| **Context Relevance** | `RelevanceEvaluator` | question + retrieved_context | relevant / irrelevant | 1 / 0 |
| **Correctness** | `QAEvaluator` | answer + reference_answer | correct / incorrect | 1 / 0 |

### Judge 모델 설정

```python
judge_model = OpenAIModel(model="gpt-4o", temperature=0.0)
# 피평가 모델(gpt-4o-mini)보다 더 강력한 모델 사용
# temperature=0.0 → 평가 결정성 최대화
# provide_explanation=True → chain-of-thought 기록 (디버깅용)
```

### Evaluator ↔ Task 출력값 컬럼 매핑

```
task 반환값:
  output = {
    "answer":             → evaluator의 output
    "retrieved_context":  → evaluator의 reference (Faithfulness, Context Relevance)
  }

dataset:
  input.question          → evaluator의 input
  output.reference_answer → evaluator의 expected (Correctness)
```

### Answer Relevance Custom 평가 프롬프트 방향

```
당신은 RAG 시스템의 답변 품질을 평가합니다.

[질문]: {question}
[답변]: {answer}

답변이 질문에 실질적으로 답하고 있습니까?
- relevant: 질문의 핵심에 답변함
- irrelevant: 질문을 회피하거나 무관한 내용을 답함
```

---

## 6. 실험 실행 설계

### `run_evaluation.py` 실행 흐름

```
python eval/run_evaluation.py \
  --datasets v1 v2 \
  --agents v1_baseline v2_gpt4o v3_k8
          ↓
1. Phoenix Client 연결 확인
2. 지정된 dataset 버전 로드 (없으면 create_dataset.py 자동 실행)
3. 지정된 agent config 목록 로드
4. (dataset, agent) 조합 매트릭스 구성
5. 각 조합에 대해 run_experiment() 실행
   experiment_name = "{agent.version}_on_{dataset.name}"
6. 완료 후 Phoenix UI URL 출력
```

### 실험 명명 규칙

```
{rag_config.version}_on_{dataset_config.name}

예:
  v1_baseline_on_ncs-rag-eval-v1
  v2_gpt4o_on_ncs-rag-eval-v1
  v3_k8_on_ncs-rag-eval-v2
```

### 집계 결과 예시 (Phoenix UI)

```
Experiment                          Faithfulness  AnswerRel  ContextRel  Correctness
v1_baseline_on_ncs-rag-eval-v1         0.72         0.81       0.65        0.68
v2_gpt4o_on_ncs-rag-eval-v1            0.89         0.91       0.65        0.84
v3_k8_on_ncs-rag-eval-v1               0.75         0.83       0.78        0.71
```

---

## 7. 의존성

```
# 신규 설치 필요
arize-phoenix-evals   # HallucinationEvaluator, QAEvaluator, RelevanceEvaluator, llm_classify

# 기존 설치됨
arize-phoenix         # px.Client(), run_experiment()
```

---

## 8. 개발 순서

```
Step 1. eval/configs.py
        DatasetConfig + RAGConfig 정의

Step 2. eval/create_dataset.py
        PGVector 청크 샘플링 → LLM Q&A 합성 → Phoenix Dataset 업로드

Step 3. eval/tasks.py
        make_task(rag_config) 팩토리 구현

Step 4. eval/evaluators.py
        4개 평가 지표 래핑 + Answer Relevance custom 구현

Step 5. eval/run_evaluation.py
        매트릭스 조합 순회 → run_experiment() 호출
```
