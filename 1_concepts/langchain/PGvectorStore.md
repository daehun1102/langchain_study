# PGVectorStore: Comprehensive Developer Guide

`PGVectorStore`는 PostgreSQL의 `pgvector` 확장을 활용하여 벡터 검색과 관계형 데이터를 통합 관리할 수 있게 해주는 LangChain 통합 패키지입니다.

---

## 1. 초기 설정 (Initialization)

`PGVectorStore`는 직접 생성자를 호출하지 않고, `create` 또는 `create_sync` 정적 메서드를 통해 인스턴스를 생성하는 것이 원칙입니다.

### 🛠️ PGEngine 설정
데이터베이스 연결 풀을 관리하는 객체로, 성능 최적화를 위해 필수적입니다.

```python
from langchain_postgres import PGEngine

# 1. Connection String 방식 (asyncpg 권장)
CONNECTION_STRING = "postgresql+asyncpg://user:password@localhost:6024/dbname"
pg_engine = PGEngine.from_connection_string(url=CONNECTION_STRING)

# 2. 기존 테이블 초기화 (선택 사항)
await pg_engine.ainit_vectorstore_table(
    table_name="my_vectors",
    vector_size=1536  # 임베딩 모델의 차원 수
)
```

---

## 2. 주요 생성 파라미터 (Parameters)

`PGVectorStore.create()` 메서드에서 사용하는 핵심 파라미터들입니다.

| 파라미터 | 타입 | 설명 | 기본값 |
| :--- | :--- | :--- | :--- |
| `engine` | `PGEngine` | DB 연결 풀 엔진 | **필수** |
| `embedding_service` | `Embeddings` | 사용할 텍스트 임베딩 모델 객체 | **필수** |
| `table_name` | `str` | 벡터 데이터를 저장할 테이블 이름 | **필수** |
| `distance_strategy` | `DistanceStrategy` | 유사도 계산 방식 (Cosine, Euclidean, MaxInnerProduct) | `COSINE_DISTANCE` |
| `content_column` | `str` | 원본 텍스트(Page Content)가 저장될 컬럼명 | `"content"` |
| `embedding_column` | `str` | 벡터 값이 저장될 컬럼명 | `"embedding"` |
| `metadata_json_column` | `str` | 메타데이터를 JSONB 형태로 저장할 컬럼명 | `"langchain_metadata"` |
| `id_column` | `str` | 문서의 고유 ID 컬럼명 | `"langchain_id"` |
| `k` | `int` | 검색 시 반환할 결과 수 | `4` |
| `hybrid_search_config` | `HybridSearchConfig` | 키워드 + 벡터 하이브리드 검색 설정 | `None` |

---

## 3. 데이터 조작 (CRUD)



### 📥 데이터 추가 (Add)
```python
from langchain_core.documents import Document

docs = [Document(page_content="삼성전자 주가 전망", metadata={"category": "stock"})]

# 비동기 추가
await store.aadd_documents(docs)

# 텍스트 직접 추가
await store.aadd_texts(["SK하이닉스 실적 발표"], metadatas=[{"category": "finance"}])
```

### 🗑️ 데이터 삭제 (Delete)
```python
# ID 리스트를 이용한 삭제
await store.adelete(ids=["uuid-1", "uuid-2"])
```

---

## 4. 검색 기능 (Search Operations)

### 🔍 유사도 검색 (Similarity Search)
가장 일반적인 검색 방식입니다.

```python
# 일반 검색
results = await store.asimilarity_search(query="반도체 공정", k=3)

# 필터링 포함 검색
results = await store.asimilarity_search(
    query="반도체",
    filter={"category": {"$eq": "technology"}}
)
```

### ⚖️ MMR 검색 (Max Marginal Relevance)
검색 결과의 **다양성**을 확보하고자 할 때 사용합니다. 유사도가 높으면서도 서로 다른 내용을 가진 문서들을 추출합니다.

```python
results = await store.amax_marginal_relevance_search(
    query="주식 투자 전략",
    k=3,
    fetch_k=10,  # 10개를 먼저 뽑은 후 그 중 가장 다양한 3개 선택
    lambda_mult=0.5  # 0에 가까울수록 다양성 극대화, 1에 가까울수록 유사도 중심
)
```

---

## 5. 인덱싱 및 성능 최적화

벡터 데이터가 많아질 경우(수만 건 이상), 검색 속도 향상을 위해 인덱스를 반드시 생성해야 합니다.

### ⚡ HNSW 인덱스 적용
가장 성능이 우수하고 범용적으로 사용되는 그래프 기반 인덱스입니다.

```python
from langchain_postgres.v2.indexes import HNSWIndex

await store.aapply_vector_index(
    HNSWIndex(name="idx_stock_vectors", m=16, ef_construction=64)
)
```

### 📏 거리 전략 (Distance Strategy)
수학적으로 유사도를 계산하는 방식입니다.

- **Cosine Distance ($1 - \cos \theta$):** 방향성의 유사도를 측정 (가장 일반적).
- **Euclidean Distance ($L2$):** 벡터 간의 직선 거리를 측정.
- **Inner Product:** 벡터의 내적 값을 측정.

---

## 6. 메타데이터 필터 연산자

필터링 시 사용할 수 있는 주요 연산자입니다.

| 연산자 | 설명 | 예시 |
| :--- | :--- | :--- |
| `$eq` | 같음 | `{"price": {"$eq": 100}}` |
| `$ne` | 같지 않음 | `{"category": {"$ne": "news"}}` |
| `$gt` / `$gte` | 초과 / 이상 | `{"date": {"$gt": "2024-01-01"}}` |
| `$in` / `$nin` | 포함 / 미포함 | `{"tag": {"$in": ["AI", "SaaS"]}}` |
| `$like` / `$ilike` | 패턴 매칭 (대소문자 구분/미구분) | `{"name": {"$ilike": "%stock%"}}` |
| `$and` / `$or` | 논리 결합 | `{"$or": [{"a": 1}, {"b": 2}]}` |

---

## 7. Clean up
```python
# 테이블 삭제 (주의: 복구 불가능)
await pg_engine.adrop_table("my_vectors")
```