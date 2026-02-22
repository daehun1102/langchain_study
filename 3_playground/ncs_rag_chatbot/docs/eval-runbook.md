# RAG 평가 시스템 실행 가이드

NCS RAG Chatbot의 버전별 품질을 Arize Phoenix로 자동 평가하는 방법을 설명합니다.

---

## 전제 조건

| 항목 | 내용 |
|------|------|
| **PostgreSQL** | `ncs_vectors` 테이블에 청크 데이터 적재 완료 |
| **Arize Phoenix** | `http://localhost:6006` 에서 실행 중 |
| **Redis** | 프롬프트 저장소 실행 중 |
| **환경 변수** | `.env` 파일 설정 완료 |

`.env` 필수 항목:

```env
OPENAI_API_KEY=sk-...
DB_CONNECTION=postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db
```

---

## 의존성 설치

```bash
cd ai_server
pip install -r requirements.txt
```

---

## 실행 흐름

```
1. 평가 데이터셋 생성 (최초 1회)
        ↓
2. 평가 실험 실행
        ↓
3. Phoenix UI에서 결과 확인
```

---

## Step 1: 평가 데이터셋 생성

PGVector에서 청크를 샘플링하고 LLM으로 Q&A 쌍을 합성해 Phoenix Dataset으로 업로드합니다.

```bash
cd ai_server

# v1 데이터셋 생성 (50개 Q&A, factual 전략)
python -m eval.create_dataset --config v1

# v2 데이터셋 생성 (100개 Q&A, mixed 전략)
python -m eval.create_dataset --config v2
```

> **참고:** 데이터셋이 Phoenix에 이미 존재하면 `run_evaluation.py`가 자동으로 재사용합니다. 수동 실행은 최초 1회 또는 데이터셋을 갱신할 때만 필요합니다.

### 데이터셋 버전

| 키 | 이름 | 샘플 수 | 전략 |
|----|------|---------|------|
| `v1` | `ncs-rag-eval-v1` | 50 | factual (사실형) |
| `v2` | `ncs-rag-eval-v2` | 100 | mixed (사실형 + 추론형) |

### DB 연결 직접 지정

```bash
python -m eval.create_dataset --config v1 \
  --db postgresql+asyncpg://user:pass@host:5432/dbname
```

---

## Step 2: 평가 실험 실행

지정한 데이터셋 × RAG 에이전트 조합으로 실험을 실행합니다.

```bash
cd ai_server

# 기본 실행: v1 데이터셋으로 베이스라인 평가
python -m eval.run_evaluation --datasets v1 --agents v1_baseline

# 전체 매트릭스: 2개 데이터셋 × 3개 에이전트 = 6개 실험
python -m eval.run_evaluation \
  --datasets v1 v2 \
  --agents v1_baseline v2_gpt4o v3_k8
```

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--datasets` | (필수) | 평가할 데이터셋 키. `v1` `v2` |
| `--agents` | (필수) | 평가할 RAG 버전 키. 아래 표 참조 |
| `--db` | `DB_CONNECTION` 환경변수 | PostgreSQL 연결 문자열 |
| `--phoenix` | `http://localhost:6006` | Phoenix 서버 주소 |
| `--judge` | `gpt-4o` | 평가 Judge 모델 |

### RAG 에이전트 버전

| 키 | 모델 | retrieval_k | 비고 |
|----|------|-------------|------|
| `v1_baseline` | gpt-4o-mini | 4 | 기준선 |
| `v2_gpt4o` | gpt-4o | 4 | 모델 업그레이드 |
| `v3_k8` | gpt-4o-mini | 8 | 검색 범위 확장 |

---

## Step 3: Phoenix UI에서 결과 확인

브라우저에서 `http://localhost:6006` 접속 → **Experiments** 탭

실험 이름 형식: `{agent_version}_on_{dataset_name}`

```
v1_baseline_on_ncs-rag-eval-v1
v2_gpt4o_on_ncs-rag-eval-v1
v3_k8_on_ncs-rag-eval-v1
```

### 평가 지표 4개

| 지표 | 설명 | 점수 |
|------|------|------|
| **Faithfulness** | 답변이 검색된 컨텍스트에 근거하는지 | 1 (factual) / 0 (hallucinated) |
| **Context Relevance** | 검색된 컨텍스트가 질문과 관련있는지 | 1 (relevant) / 0 (irrelevant) |
| **Correctness** | 답변이 reference_answer와 일치하는지 | 1 (correct) / 0 (incorrect) |
| **Answer Relevance** | 답변이 질문에 직접 답하는지 | 1 (relevant) / 0 (irrelevant) |

---

## 새 RAG 버전 추가 방법

`ai_server/eval/configs.py`에 `RAGConfig`를 추가하고 레지스트리에 등록합니다.

**1. configs.py에 버전 추가:**

```python
V4_CUSTOM = RAGConfig(
    version="v4_custom",
    model_name="gpt-4o-mini",
    retrieval_k=4,
    prompt_override={"agent_system_prompt": "커스텀 시스템 프롬프트"},
)
```

**2. run_evaluation.py의 `_AGENT_REGISTRY`에 등록:**

```python
_AGENT_REGISTRY = {
    "v1_baseline": V1_BASELINE,
    "v2_gpt4o": V2_GPT4O,
    "v3_k8": V3_K8,
    "v4_custom": V4_CUSTOM,   # 추가
}
```

**3. 실험 실행:**

```bash
python -m eval.run_evaluation --datasets v1 --agents v4_custom
```

---

## 자주 발생하는 문제

**`ModuleNotFoundError: No module named 'eval'`**
→ `ai_server/` 디렉토리에서 실행해야 합니다. `cd ai_server` 후 재실행.

**Phoenix 연결 오류**
→ Phoenix가 실행 중인지 확인: `curl http://localhost:6006/health`

**데이터셋 생성 중 DB 오류**
→ `DB_CONNECTION` 환경변수 또는 `--db` 옵션의 연결 문자열을 확인합니다.

**OpenAI API 오류**
→ `OPENAI_API_KEY`가 `.env`에 설정되어 있는지 확인합니다.
