# NCS RAG Chatbot

NCS(국가직무능력표준) 문서를 기반으로 질문에 답변하는 RAG(Retrieval-Augmented Generation) 챗봇입니다.
PostgreSQL의 `pgvector` 확장을 사용하여 벡터 유사도 검색을 수행하며, 메타데이터 필터링을 통해 검색 정확도를 높입니다.

## 🛠️ 설치 및 설정 (Setup)

### 1. 필수 조건 (Prerequisites)
- **Python 3.10+**
- **PostgreSQL** (with `pgvector` extension installed)
- **OpenAI API Key**

### 2. 가상환경 및 패키지 설치
```bash
# 가상환경 생성 (선택사항)
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate

# 패키지 설치
pip install fastapi uvicorn python-dotenv langchain-openai langchain-postgres sqlalchemy[asyncio] asyncpg pydantic
```

### 3. 환경 변수 설정
프로젝트 루트에 `.env` 파일을 생성하고 다음 변수를 설정하세요.
```ini
OPENAI_API_KEY=sk-your-api-key-here
# DB 연결 문자열 예시: postgresql+asyncpg://user:password@host:port/dbname
DB_CONNECTION=postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db
```

## 🚀 실행 방법 (How to Run)

### 1. 데이터 적재 (Ingestion)
PDF 문서들을 벡터 DB에 적재합니다. `src/ingest.py` 스크립트를 실행하면 `assets/실습 NCS파일` 경로의 PDF 파일들을 읽어 임베딩 후 저장합니다.

```bash
python src/ingest.py
```
> **참고**: 최초 실행 시 테이블(`test_table_filtered`)이 자동으로 생성됩니다.

### 2. 서버 실행 (Run Server)
FastAPI 서버를 실행합니다.

```bash
uvicorn server:app --reload
```
서버가 시작되면 [http://localhost:8000](http://localhost:8000) (또는 설정된 포트)에서 접속 가능합니다.
- API 문서: [http://localhost:8000/docs](http://localhost:8000/docs)
- 채팅 API: `POST /api/chat`

---

## 🔍 PGVector 필터링 구현 방법

이 프로젝트는 `langchain-postgres` 라이브러리의 `PGVectorStore`를 사용하여 메타데이터 기반 필터링을 구현했습니다. 이를 통해 대분류/중분류와 같은 특정 카테고리 내에서만 유사도 검색을 수행할 수 있습니다.

### 1. 메타데이터 컬럼 정의 (Table Schema)
`PGVectorStore`는 JSONB 컬럼에 모든 메타데이터를 저장하는 방식 외에도, **별도의 관계형 컬럼(Relational Columns)** 으로 메타데이터를 분리하여 저장할 수 있습니다. 이렇게 하면 SQL의 `WHERE` 절을 효율적으로 사용할 수 있어 검색 속도와 정확도가 향상됩니다.

`src/ingest.py`에서 테이블 생성 시 다음과 같이 메타데이터 컬럼을 명시적으로 정의했습니다:

```python
# src/ingest.py

METADATA_COLUMNS = [
    Column("main_category", "VARCHAR", nullable=True),
    Column("sub_category", "VARCHAR", nullable=True),
    Column("source", "VARCHAR", nullable=True),
    Column("page", "INTEGER", nullable=True),
]

# ...

await pg_engine.ainit_vectorstore_table(
    table_name="test_table_filtered",
    vector_size=1536,
    metadata_columns=METADATA_COLUMNS,  # 정의된 컬럼 적용
    overwrite_existing=True,
)
```

### 2. 벡터 저장소 초기화
데이터를 적재하거나 검색할 때 `PGVectorStore`를 생성하면서 `metadata_columns` 리스트를 전달해야 라이브러리가 해당 컬럼들을 인식합니다.

```python
# src/vector_store.py

vector_store = await PGVectorStore.create(
    engine=pg_engine,
    table_name=table_name,
    embedding_service=embedding_model,
    metadata_columns=["main_category", "sub_category", "source", "page"], # 중요!
)
```

### 3. 필터링을 적용한 검색 (Filtering during Search)
사용자가 API를 호출할 때 `main_category`나 `sub_category`를 지정하면, `server.py`에서 이를 필터 딕셔너리로 변환하여 검색 메서드에 전달합니다.

```python
# server.py

filt = {}
if req.main_category:
    filt["main_category"] = {"$eq": req.main_category} # 정확히 일치하는($eq) 조건
if req.sub_category:
    filt["sub_category"] = {"$eq": req.sub_category}

# 벡터 검색 실행 (filter 적용)
docs = await store.asimilarity_search(req.query, k=4, filter=filt)
```

**작동 원리**:
1. `filter` 인자가 `langchain-postgres` 내부에서 SQL 쿼리의 `WHERE` 절로 변환됩니다.
2. `metadata_columns`로 정의된 실제 DB 컬럼(`main_category`, `sub_category`)을 대상으로 조건이 적용됩니다.
3. 해당 조건을 만족하는 행(Row)들 중에서 벡터 유사도(`User Query Embedding` <-> `Stored Embedding`)가 가장 높은 상위 `k`개를 반환합니다.

이 방식은 벡터 유사도만으로는 구분하기 어려운 문맥(예: 다른 카테고리의 유사한 내용 배제)을 명확히 분리하는 데 매우 효과적입니다.
