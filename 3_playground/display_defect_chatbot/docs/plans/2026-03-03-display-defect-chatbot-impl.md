# Display Defect Chatbot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 삼성 디스플레이 픽셀 불량/반송 분석 챗봇 — RAG 가설 생성 후 LangGraph Send API로 4개 서브에이전트 병렬 실행, 장기 이력 에이전트는 asyncio 백그라운드 Task로 처리

**Architecture:** FastAPI가 두 단계 API를 제공 (1. RAG 가설 생성, 2. Send API 병렬 서브에이전트). Spring Boot가 프론트-AI서버 간 프록시. PostgreSQL 단일 DB로 relational + PGVector 처리.

**Tech Stack:** FastAPI 0.128, LangGraph 1.0.8 (Send API), LangChain 1.2, OpenAI gpt-4o-mini, SQLAlchemy 2.0 async, PostgreSQL+pgvector, Spring Boot 4.0.2 (Java 17, MyBatis 4.0.1), Vue 3 + Vite, Docker Compose

**참조 프로젝트:** `ncs_rag_chatbot/` — 동일 스택, 패턴 재사용

---

## Task 1: 프로젝트 스캐폴딩

**Files:**
- Create: `display_defect_chatbot/.gitignore`
- Create: `display_defect_chatbot/.env`
- Create: `display_defect_chatbot/ai_server/mock_data/pixel_failure_cases.txt`
- Create: `display_defect_chatbot/ai_server/mock_data/process_sop.txt`

**Step 1: .gitignore 생성**

```
# display_defect_chatbot/.gitignore
.env
__pycache__/
*.pyc
*.class
target/
node_modules/
dist/
.venv/
*.log
uploads/
bg_results/
```

**Step 2: .env 생성**

```
# display_defect_chatbot/.env
OPENAI_API_KEY=sk-...

# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=1234
POSTGRES_DB=defect_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# AI Server
AI_SERVER_URL=http://ai-server:8000
INTERNAL_AI_SERVER_URL=http://ai-server:8000

# Phoenix (optional)
PHOENIX_COLLECTOR_ENDPOINT=http://phoenix:4317
```

**Step 3: Mock txt 문서 생성**

```
# ai_server/mock_data/pixel_failure_cases.txt
[CASE-001] 픽셀 불량 유형: Dead Pixel (완전 소등)
발생 공정: Array 공정 - TFT 제조 단계
추정 원인 1: TFT(박막 트랜지스터) 게이트 전극 단락
  - 증상: 특정 행/열 픽셀이 완전히 꺼짐
  - 발생 빈도: CVD 장비 파티클 오염 시 집중 발생
  - 조치: CVD 챔버 클리닝 후 게이트 절연막 두께 재측정
추정 원인 2: 데이터 라인 단선
  - 증상: 세로 방향 줄무늬 불량
  - 조치: 리페어 레이저로 단선 부위 재연결

[CASE-002] 픽셀 불량 유형: Hot Pixel (항상 점등)
발생 공정: Cell 공정 - 액정 주입 단계
추정 원인 1: 픽셀 전극 쇼트
  - 증상: 흰 점 형태로 항상 점등
  - 발생 패턴: 가장자리 영역 집중
  - 조치: 공정 마진 재검토, 전극 간격 확대

[CASE-003] 픽셀 불량 유형: Stuck Pixel (특정 색상 고착)
발생 공정: Module 공정 - 드라이버 IC 본딩
추정 원인: 드라이버 IC 불량 출력
  - 증상: RGB 중 특정 색상만 지속 출력
  - 조치: IC 재본딩 또는 교체, 구동 전압 재설정

[CASE-004] 픽셀 불량 유형: 군집 불량 (Cluster Defect)
발생 공정: Array 공정 - 포토 공정
추정 원인: 마스크 이물질 부착
  - 증상: 특정 영역 픽셀 다수 동시 불량
  - 발생 환경: 클린룸 파티클 증가 시
  - 조치: 마스크 세정, 클린룸 파티클 모니터링 강화
```

```
# ai_server/mock_data/process_sop.txt
[SOP-PIXEL-001] 픽셀 불량 초기 대응 절차
1. 불량 스크린샷 및 좌표 기록 (픽셀 위치 정확히 특정)
2. 불량 유형 분류: Dead/Hot/Stuck/Cluster
3. 발생 로트번호 및 장비 ID 확인
4. 동일 장비에서 생산된 인접 로트 추가 검사

[SOP-TFT-002] TFT 불량 공정 대응
1. CVD 장비 파티클 카운터 확인 (기준: 0.1μm 이상 10개/L 이하)
2. 기준 초과 시: 챔버 즉시 클리닝 후 더미 웨이퍼 투입
3. TFT 특성 측정: Vth, Mobility, Ion/Ioff 비율
4. 불량 판정 기준: Ion/Ioff < 10^6 → 불량

[SOP-RETURN-001] 반송 처리 절차
1. 반송 접수 후 24시간 내 원인 분석 착수
2. 반송 제품 분리 보관 (정상 제품과 혼입 방지)
3. 고객사 반송 사유서 수령 및 내부 분석 결과 대조
4. 재발 방지 대책 수립 후 8D 보고서 작성

[SOP-BG-ANALYSIS-001] 장기 이력 분석 절차
1. 해당 제품 모델 6개월치 불량률 추이 추출
2. 공정별 불량 기여도 분석 (파레토 차트)
3. 동일 불량 유형 반복 발생 여부 확인
4. 계절성/장비 교체 이력과의 상관관계 분석
```

**Step 4: 커밋**

```bash
git add display_defect_chatbot/
git commit -m "chore: display_defect_chatbot 프로젝트 스캐폴딩 및 Mock 문서 추가"
```

---

## Task 2: Docker Compose

**Files:**
- Create: `display_defect_chatbot/docker-compose.yml`
- Create: `display_defect_chatbot/ai_server/Dockerfile`
- Create: `display_defect_chatbot/frontend/Dockerfile`

**Step 1: docker-compose.yml 생성**

```yaml
# display_defect_chatbot/docker-compose.yml
services:

  postgres:
    image: pgvector/pgvector:pg16
    container_name: defect-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: "1234"
      POSTGRES_DB: defect_db
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d defect_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - defect-network

  phoenix:
    image: arizephoenix/phoenix:latest
    container_name: defect-phoenix
    restart: unless-stopped
    ports:
      - "6007:6006"
      - "4318:4317"
    volumes:
      - phoenix_data:/phoenix/.phoenix
    networks:
      - defect-network

  ai-server:
    build:
      context: .
      dockerfile: ai_server/Dockerfile
    container_name: defect-ai-server
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "8001:8000"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - defect-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: defect-backend
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "8081:8080"
    depends_on:
      - ai-server
    networks:
      - defect-network
    extra_hosts:
      - "host.docker.internal:host-gateway"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: defect-frontend
    restart: unless-stopped
    ports:
      - "5175:5174"
    depends_on:
      - backend
    networks:
      - defect-network

networks:
  defect-network:
    driver: bridge

volumes:
  postgres_data:
  phoenix_data:
```

**Step 2: ai_server/Dockerfile 생성**

```dockerfile
# display_defect_chatbot/ai_server/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY ai_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ai_server/ ./ai_server/

WORKDIR /app/ai_server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 3: frontend/Dockerfile 생성**

```dockerfile
# display_defect_chatbot/frontend/Dockerfile
FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5174
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5174"]
```

**Step 4: 커밋**

```bash
git add display_defect_chatbot/
git commit -m "feat(docker): display_defect_chatbot Docker Compose 및 Dockerfile 추가"
```

---

## Task 3: PostgreSQL 스키마 + Mock 데이터

**Files:**
- Create: `display_defect_chatbot/db/init.sql`

**Step 1: init.sql 생성**

```sql
-- display_defect_chatbot/db/init.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- 문서 레지스트리
CREATE TABLE IF NOT EXISTS documents (
    doc_id      VARCHAR(100) PRIMARY KEY,
    filename    VARCHAR(255) NOT NULL,
    doc_type    VARCHAR(50),
    status      VARCHAR(20) DEFAULT 'PENDING',
    created_at  TIMESTAMP DEFAULT NOW()
);

-- 제품 마스터
CREATE TABLE IF NOT EXISTS products (
    product_id      VARCHAR(50) PRIMARY KEY,
    model           VARCHAR(100),
    panel_size      VARCHAR(20),
    manufactured_at TIMESTAMP
);

-- 불량 케이스
CREATE TABLE IF NOT EXISTS defect_cases (
    case_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id   VARCHAR(50) REFERENCES products(product_id),
    company      VARCHAR(100),
    defect_type  VARCHAR(100),
    description  TEXT,
    reported_at  TIMESTAMP DEFAULT NOW()
);

-- 공정이력 (ProcessHistoryAgent)
CREATE TABLE IF NOT EXISTS process_history (
    id           BIGSERIAL PRIMARY KEY,
    product_id   VARCHAR(50),
    process_step VARCHAR(100),
    equipment_id VARCHAR(50),
    operator_id  VARCHAR(50),
    result       VARCHAR(20),
    measured_at  TIMESTAMP
);

-- 반송이력 (ReturnHistoryAgent)
CREATE TABLE IF NOT EXISTS return_history (
    id            BIGSERIAL PRIMARY KEY,
    product_id    VARCHAR(50),
    return_reason VARCHAR(200),
    return_date   DATE,
    quantity      INT,
    severity      VARCHAR(20)
);

-- 테스트결과 (TestResultAgent)
CREATE TABLE IF NOT EXISTS test_results (
    id              BIGSERIAL PRIMARY KEY,
    product_id      VARCHAR(50),
    test_type       VARCHAR(100),
    result          VARCHAR(20),
    measured_value  DECIMAL,
    spec_min        DECIMAL,
    spec_max        DECIMAL,
    tested_at       TIMESTAMP
);

-- 백그라운드 작업 추적
CREATE TABLE IF NOT EXISTS background_tasks (
    id           BIGSERIAL PRIMARY KEY,
    task_id      VARCHAR(100) UNIQUE NOT NULL,
    session_id   VARCHAR(100),
    status       VARCHAR(20) DEFAULT 'PENDING',
    result_text  TEXT,
    created_at   TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- ── Mock 데이터 ────────────────────────────────────────────────

INSERT INTO products VALUES
  ('LOT-A001', 'SDC-OLED-55A', '55inch', '2025-06-01'),
  ('LOT-A002', 'SDC-OLED-55A', '55inch', '2025-06-15'),
  ('LOT-B001', 'SDC-QLED-65B', '65inch', '2025-07-01'),
  ('LOT-C001', 'SDC-OLED-27C', '27inch', '2025-08-01')
ON CONFLICT DO NOTHING;

INSERT INTO defect_cases (product_id, company, defect_type, description) VALUES
  ('LOT-A001', 'A사', 'Dead Pixel', '화면 좌측 상단 영역 픽셀 소등 불량 10개'),
  ('LOT-A002', 'B사', 'Hot Pixel', '화면 중앙부 흰 점 불량 5개'),
  ('LOT-B001', 'A사', 'Cluster Defect', '우측 하단 군집 불량 50x50px')
ON CONFLICT DO NOTHING;

INSERT INTO process_history (product_id, process_step, equipment_id, operator_id, result, measured_at) VALUES
  ('LOT-A001', 'CVD-Gate', 'EQ-CVD-01', 'OP-100', 'PASS', '2025-06-01 08:00:00'),
  ('LOT-A001', 'Photo-Gate', 'EQ-PHT-02', 'OP-101', 'PASS', '2025-06-01 10:00:00'),
  ('LOT-A001', 'Etch-Gate', 'EQ-ETH-01', 'OP-102', 'FAIL', '2025-06-01 12:00:00'),
  ('LOT-A001', 'CVD-Active', 'EQ-CVD-01', 'OP-100', 'WARN', '2025-06-01 14:00:00'),
  ('LOT-A001', 'Ion-Implant', 'EQ-ION-01', 'OP-103', 'PASS', '2025-06-01 16:00:00'),
  ('LOT-A002', 'CVD-Gate', 'EQ-CVD-02', 'OP-100', 'PASS', '2025-06-15 08:00:00'),
  ('LOT-A002', 'Cell-Align', 'EQ-ALN-01', 'OP-104', 'FAIL', '2025-06-15 14:00:00'),
  ('LOT-B001', 'Photo-Gate', 'EQ-PHT-01', 'OP-101', 'WARN', '2025-07-01 09:00:00');

INSERT INTO return_history (product_id, return_reason, return_date, quantity, severity) VALUES
  ('LOT-A001', '픽셀 소등 불량 - TFT 불량 의심', '2025-07-10', 50, 'HIGH'),
  ('LOT-A001', '화면 얼룩 - 공정 불량', '2025-07-15', 20, 'MEDIUM'),
  ('LOT-A002', '백라이트 불균일', '2025-07-20', 30, 'LOW'),
  ('LOT-B001', '군집 픽셀 불량 - 마스크 오염 의심', '2025-08-05', 80, 'HIGH');

INSERT INTO test_results (product_id, test_type, result, measured_value, spec_min, spec_max, tested_at) VALUES
  ('LOT-A001', 'Vth-Uniformity', 'FAIL', 2.8, 1.0, 2.5, '2025-06-02 09:00:00'),
  ('LOT-A001', 'Ion/Ioff-Ratio', 'PASS', 1200000, 1000000, NULL, '2025-06-02 09:30:00'),
  ('LOT-A001', 'Mobility', 'WARN', 0.45, 0.5, 1.5, '2025-06-02 10:00:00'),
  ('LOT-A002', 'Cell-Gap', 'FAIL', 3.8, 4.0, 4.5, '2025-06-16 09:00:00'),
  ('LOT-A002', 'Vth-Uniformity', 'PASS', 1.8, 1.0, 2.5, '2025-06-16 09:30:00'),
  ('LOT-B001', 'Particle-Count', 'FAIL', 18, 0, 10, '2025-07-02 08:00:00'),
  ('LOT-B001', 'CD-Uniformity', 'WARN', 98.2, 99.0, 101.0, '2025-07-02 08:30:00');
```

**Step 2: 검증 — Docker로 DB 기동 후 확인**

```bash
cd display_defect_chatbot
docker compose up postgres -d
docker exec -it defect-postgres psql -U postgres -d defect_db -c "\dt"
# Expected: documents, products, defect_cases, process_history, return_history, test_results, background_tasks
docker exec -it defect-postgres psql -U postgres -d defect_db -c "SELECT count(*) FROM process_history;"
# Expected: 8
```

**Step 3: 커밋**

```bash
git add display_defect_chatbot/db/
git commit -m "feat(db): PostgreSQL 스키마 및 Mock 데이터 init.sql 추가"
```

---

## Task 4: ai_server 기반 설정

**Files:**
- Create: `display_defect_chatbot/ai_server/requirements.txt`
- Create: `display_defect_chatbot/ai_server/config.py`

**Step 1: requirements.txt 생성 (ncs_rag_chatbot 기반, Redis/Oracle 제거)**

```
fastapi==0.128.7
uvicorn==0.40.0
pydantic==2.12.5
pydantic-settings==2.12.0
python-dotenv==1.2.1

# LangChain / LangGraph
langchain==1.2.9
langchain-core==1.2.9
langchain-openai==1.1.7
langchain-postgres==0.0.16
langchain-text-splitters==1.1.0
langgraph==1.0.8
langgraph-checkpoint==4.0.0
langgraph-prebuilt==1.0.7

# OpenAI
openai==2.17.0
tiktoken==0.12.0

# PostgreSQL async
SQLAlchemy==2.0.46
asyncpg==0.31.0
psycopg==3.3.2
psycopg-binary==3.3.2
psycopg-pool==3.3.0
psycopg2-binary==2.9.11
pgvector==0.3.6

# Utils
httpx==0.28.1
anyio==4.12.1
python-multipart==0.0.20

# Tracing (optional)
arize-phoenix-otel==0.14.0
openinference-instrumentation-langchain==0.1.59
opentelemetry-exporter-otlp==1.39.1
```

**Step 2: config.py 생성**

```python
# display_defect_chatbot/ai_server/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    openai_api_key: str
    postgres_user: str = "postgres"
    postgres_password: str = "1234"
    postgres_db: str = "defect_db"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    phoenix_collector_endpoint: str = "http://phoenix:4317"

    class Config:
        env_file = ".env"

    @property
    def pg_async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def pg_sync_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Step 3: 커밋**

```bash
git add display_defect_chatbot/ai_server/
git commit -m "feat(ai-server): requirements.txt 및 config.py 추가"
```

---

## Task 5: ai_server 인프라 레이어

**Files:**
- Create: `display_defect_chatbot/ai_server/infra/__init__.py`
- Create: `display_defect_chatbot/ai_server/infra/vector_store.py`
- Create: `display_defect_chatbot/ai_server/infra/database.py`
- Create: `display_defect_chatbot/ai_server/infra/ingest.py`
- Create: `display_defect_chatbot/ai_server/infra/tracing.py`

**Step 1: vector_store.py (ncs_rag_chatbot 참조, 테이블명만 변경)**

```python
# display_defect_chatbot/ai_server/infra/vector_store.py
from langchain_postgres import PGEngine, PGVectorStore, Column
from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import create_async_engine
from typing import List, Optional

TABLE_NAME = "defect_vectors"
VECTOR_SIZE = 1536  # text-embedding-3-small
METADATA_COLUMNS = [
    Column("doc_id", "VARCHAR", nullable=True),
    Column("chunk_index", "INTEGER", nullable=True),
]


class VectorStoreManager:
    def __init__(self, pg_engine, vector_store):
        self.pg_engine = pg_engine
        self.vector_store = vector_store

    @classmethod
    async def create(cls, connection_string: str, embedding_model):
        engine = create_async_engine(connection_string)
        pg_engine = PGEngine.from_engine(engine)
        await pg_engine.ainit_vectorstore_table(
            table_name=TABLE_NAME,
            vector_size=VECTOR_SIZE,
            metadata_columns=METADATA_COLUMNS,
            overwrite_existing=False,
        )
        vector_store = await PGVectorStore.create(
            engine=pg_engine,
            table_name=TABLE_NAME,
            embedding_service=embedding_model,
            metadata_columns=["doc_id", "chunk_index"],
        )
        return cls(pg_engine, vector_store)

    async def similarity_search(self, query: str, doc_ids: Optional[List[str]] = None, k: int = 4) -> List[Document]:
        if doc_ids:
            return await self.vector_store.asimilarity_search(
                query, k=k, filter={"doc_id": {"$in": doc_ids}}
            )
        return await self.vector_store.asimilarity_search(query, k=k)

    async def delete_by_doc_id(self, doc_id: str) -> int:
        from sqlalchemy import text
        engine = self.pg_engine._pool
        async with engine.begin() as conn:
            result = await conn.execute(
                text(f"DELETE FROM {TABLE_NAME} WHERE doc_id = :doc_id"),
                {"doc_id": doc_id},
            )
            return result.rowcount
```

**Step 2: database.py (SQLAlchemy async 세션)**

```python
# display_defect_chatbot/ai_server/infra/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager
from ai_server.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.pg_async_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


@asynccontextmanager
async def get_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Step 3: ingest.py (txt 파일 → PGVector 색인)**

```python
# display_defect_chatbot/ai_server/infra/ingest.py
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from ai_server.infra.vector_store import VectorStoreManager


async def ingest_document(doc_id: str, file_path: str, vsm: VectorStoreManager) -> int:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(content)

    docs = [
        Document(
            page_content=chunk,
            metadata={"doc_id": doc_id, "chunk_index": i},
        )
        for i, chunk in enumerate(chunks)
    ]

    await vsm.vector_store.aadd_documents(docs)
    return len(docs)
```

**Step 4: tracing.py**

```python
# display_defect_chatbot/ai_server/infra/tracing.py
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from openinference.instrumentation.langchain import LangChainInstrumentor


def setup_tracing(endpoint: str):
    try:
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    except Exception:
        pass  # Tracing is optional
```

**Step 5: 커밋**

```bash
git add display_defect_chatbot/ai_server/infra/
git commit -m "feat(ai-server): 인프라 레이어 추가 (vector_store, database, ingest, tracing)"
```

---

## Task 6: RAG Tool + SQL Tools

**Files:**
- Create: `display_defect_chatbot/ai_server/tools/__init__.py`
- Create: `display_defect_chatbot/ai_server/tools/rag_tool.py`
- Create: `display_defect_chatbot/ai_server/tools/sql_tools.py`

**Step 1: rag_tool.py**

```python
# display_defect_chatbot/ai_server/tools/rag_tool.py
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from ai_server.infra.vector_store import VectorStoreManager


def build_rag_tool(vsm: VectorStoreManager):
    @tool
    async def search_defect_knowledge(query: str, config: RunnableConfig) -> str:
        """과거 불량 사례 및 SOP 문서에서 관련 정보를 검색합니다."""
        doc_ids = config.get("configurable", {}).get("doc_ids")
        docs = await vsm.similarity_search(query, doc_ids=doc_ids, k=4)
        if not docs:
            return "관련 문서를 찾을 수 없습니다."
        return "\n\n".join([f"[{i+1}] {d.page_content}" for i, d in enumerate(docs)])

    return search_defect_knowledge
```

**Step 2: sql_tools.py (SQLAlchemy async 조회 함수들)**

```python
# display_defect_chatbot/ai_server/tools/sql_tools.py
from sqlalchemy import text
from ai_server.infra.database import get_db_session
from typing import Any


async def query_process_history(product_id: str) -> list[dict[str, Any]]:
    """공정이력 테이블 조회"""
    async with get_db_session() as session:
        result = await session.execute(
            text("""
                SELECT process_step, equipment_id, operator_id, result, measured_at
                FROM process_history
                WHERE product_id = :pid
                ORDER BY measured_at DESC
                LIMIT 20
            """),
            {"pid": product_id},
        )
        rows = result.mappings().all()
        return [dict(r) for r in rows]


async def query_return_history(product_id: str) -> list[dict[str, Any]]:
    """반송이력 테이블 조회"""
    async with get_db_session() as session:
        result = await session.execute(
            text("""
                SELECT return_reason, return_date, quantity, severity
                FROM return_history
                WHERE product_id = :pid
                ORDER BY return_date DESC
                LIMIT 10
            """),
            {"pid": product_id},
        )
        rows = result.mappings().all()
        return [dict(r) for r in rows]


async def query_test_results(product_id: str) -> list[dict[str, Any]]:
    """테스트결과 테이블 조회"""
    async with get_db_session() as session:
        result = await session.execute(
            text("""
                SELECT test_type, result, measured_value, spec_min, spec_max, tested_at
                FROM test_results
                WHERE product_id = :pid
                ORDER BY tested_at DESC
                LIMIT 20
            """),
            {"pid": product_id},
        )
        rows = result.mappings().all()
        return [dict(r) for r in rows]


async def query_long_term_history(product_id: str) -> str:
    """장기 이력 분석 (모델 기준 6개월 불량 통계)"""
    async with get_db_session() as session:
        # 모델명 조회
        prod = await session.execute(
            text("SELECT model FROM products WHERE product_id = :pid"),
            {"pid": product_id},
        )
        product = prod.mappings().first()
        model = product["model"] if product else "UNKNOWN"

        # 공정 불량률 통계
        stats = await session.execute(
            text("""
                SELECT ph.process_step,
                       COUNT(*) as total,
                       SUM(CASE WHEN ph.result = 'FAIL' THEN 1 ELSE 0 END) as fail_count
                FROM process_history ph
                JOIN products p ON ph.product_id = p.product_id
                WHERE p.model = :model
                GROUP BY ph.process_step
                ORDER BY fail_count DESC
            """),
            {"model": model},
        )
        rows = stats.mappings().all()

        lines = [f"[장기 이력 분석] 모델: {model}"]
        lines.append("공정별 불량 통계 (최근 6개월):")
        for r in rows:
            rate = (r["fail_count"] / r["total"] * 100) if r["total"] > 0 else 0
            lines.append(f"  {r['process_step']}: {r['fail_count']}/{r['total']} ({rate:.1f}% FAIL)")

        return "\n".join(lines)
```

**Step 3: 커밋**

```bash
git add display_defect_chatbot/ai_server/tools/
git commit -m "feat(ai-server): RAG tool 및 SQL query functions 추가"
```

---

## Task 7: 서브에이전트 4종

**Files:**
- Create: `display_defect_chatbot/ai_server/agents/__init__.py`
- Create: `display_defect_chatbot/ai_server/agents/sub/__init__.py`
- Create: `display_defect_chatbot/ai_server/agents/sub/process_history.py`
- Create: `display_defect_chatbot/ai_server/agents/sub/return_history.py`
- Create: `display_defect_chatbot/ai_server/agents/sub/test_result.py`
- Create: `display_defect_chatbot/ai_server/agents/sub/long_term.py`

**Step 1: process_history.py**

```python
# display_defect_chatbot/ai_server/agents/sub/process_history.py
from ai_server.tools.sql_tools import query_process_history


async def process_history_node(state: dict) -> dict:
    """공정이력 서브에이전트: process_history 테이블 조회"""
    product_id = state.get("product_id", "")
    rows = await query_process_history(product_id)
    return {"process_history_result": rows}
```

**Step 2: return_history.py**

```python
# display_defect_chatbot/ai_server/agents/sub/return_history.py
from ai_server.tools.sql_tools import query_return_history


async def return_history_node(state: dict) -> dict:
    """반송이력 서브에이전트: return_history 테이블 조회"""
    product_id = state.get("product_id", "")
    rows = await query_return_history(product_id)
    return {"return_history_result": rows}
```

**Step 3: test_result.py**

```python
# display_defect_chatbot/ai_server/agents/sub/test_result.py
from ai_server.tools.sql_tools import query_test_results


async def test_result_node(state: dict) -> dict:
    """테스트결과 서브에이전트: test_results 테이블 조회"""
    product_id = state.get("product_id", "")
    rows = await query_test_results(product_id)
    return {"test_result": rows}
```

**Step 4: long_term.py (asyncio 백그라운드 Task)**

```python
# display_defect_chatbot/ai_server/agents/sub/long_term.py
import asyncio
from uuid import uuid4
from datetime import datetime
from sqlalchemy import text

from ai_server.tools.sql_tools import query_long_term_history
from ai_server.infra.database import get_db_session


async def long_term_node(state: dict) -> dict:
    """장기이력 에이전트: 백그라운드로 실행, 즉시 task_id 반환"""
    task_id = str(uuid4())
    product_id = state.get("product_id", "")
    session_id = state.get("session_id", "")
    hypothesis = state.get("selected_hypothesis", "")

    # DB에 PENDING 레코드 삽입
    async with get_db_session() as session:
        await session.execute(
            text("""
                INSERT INTO background_tasks (task_id, session_id, status)
                VALUES (:task_id, :session_id, 'PENDING')
            """),
            {"task_id": task_id, "session_id": session_id},
        )

    # 백그라운드 태스크 시작 (논블로킹)
    asyncio.create_task(_run_long_term_analysis(task_id, product_id, hypothesis))

    return {"long_term_task_id": [task_id]}


async def _run_long_term_analysis(task_id: str, product_id: str, hypothesis: str):
    """장기 이력 분석 실행 (수 초 ~ 수십 초 소요 시뮬레이션)"""
    await asyncio.sleep(10)  # Mock: 실제 분석 시간 시뮬레이션

    try:
        result_text = await query_long_term_history(product_id)
        result_text += f"\n\n[선택된 가설에 기반한 추가 분석]\n{hypothesis}를 중심으로 6개월 추이를 분석한 결과, 재발 방지를 위한 공정 파라미터 조정이 필요합니다."

        async with get_db_session() as session:
            await session.execute(
                text("""
                    UPDATE background_tasks
                    SET status = 'COMPLETED', result_text = :result, completed_at = :now
                    WHERE task_id = :task_id
                """),
                {"task_id": task_id, "result": result_text, "now": datetime.now()},
            )
    except Exception as e:
        async with get_db_session() as session:
            await session.execute(
                text("UPDATE background_tasks SET status = 'FAILED' WHERE task_id = :task_id"),
                {"task_id": task_id},
            )
```

**Step 5: 커밋**

```bash
git add display_defect_chatbot/ai_server/agents/
git commit -m "feat(ai-server): 4개 서브에이전트 추가 (공정/반송/테스트/장기이력)"
```

---

## Task 8: 메인 분석 에이전트 + 종합 노드

**Files:**
- Create: `display_defect_chatbot/ai_server/agents/main_agent.py`
- Create: `display_defect_chatbot/ai_server/agents/synthesis_node.py`

**Step 1: main_agent.py (RAG 기반 가설 생성)**

```python
# display_defect_chatbot/ai_server/agents/main_agent.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ai_server.infra.vector_store import VectorStoreManager
from ai_server.config import get_settings

settings = get_settings()

HYPOTHESIS_SYSTEM_PROMPT = """당신은 삼성 디스플레이 제조 공정 전문가입니다.
사용자가 보고한 픽셀 불량 증상과 과거 사례 문서를 바탕으로
원인 가설을 정확히 2-3개 제시하세요.

응답 형식 (반드시 준수):
가설1: [원인명] — [간단한 설명]
가설2: [원인명] — [간단한 설명]
가설3: [원인명] — [간단한 설명] (선택)

각 가설은 한 줄로 간결하게 작성하세요."""


async def run_main_analysis(
    defect_description: str,
    company: str,
    vsm: VectorStoreManager,
) -> list[str]:
    """RAG로 과거 사례 검색 후 원인 가설 2-3개 생성"""
    docs = await vsm.similarity_search(defect_description, k=4)
    context = "\n\n".join([d.page_content for d in docs]) if docs else "관련 사례 없음"

    llm = ChatOpenAI(model=settings.model_name, temperature=0.3)
    messages = [
        SystemMessage(content=HYPOTHESIS_SYSTEM_PROMPT),
        HumanMessage(
            content=f"[보고 회사]: {company}\n[불량 증상]: {defect_description}\n\n[과거 사례 문서]\n{context}"
        ),
    ]
    response = await llm.ainvoke(messages)
    text = response.content.strip()

    # "가설N: ..." 패턴 파싱
    hypotheses = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("가설") and ":" in line:
            hypotheses.append(line)

    return hypotheses if hypotheses else [text]
```

**Step 2: synthesis_node.py (3개 서브에이전트 결과 종합)**

```python
# display_defect_chatbot/ai_server/agents/synthesis_node.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ai_server.config import get_settings
import json

settings = get_settings()

SYNTHESIS_SYSTEM_PROMPT = """당신은 삼성 디스플레이 품질관리 전문가입니다.
공정이력, 반송이력, 테스트결과 데이터를 종합하여 구체적인 조치 방안을 제시하세요.

응답 구조:
## 원인 분석 요약
(선택된 가설 + 수집 데이터 기반 분석)

## 즉시 조치 사항
1. ...
2. ...

## 재발 방지 대책
1. ...
2. ...

## 추가 확인 필요 사항
- ..."""


async def synthesis_node(state: dict) -> dict:
    """서브에이전트 3종 결과를 종합하여 최종 조치안 생성"""
    llm = ChatOpenAI(model=settings.model_name, temperature=0.2)

    def fmt(data: list) -> str:
        if not data:
            return "데이터 없음"
        return json.dumps(data, ensure_ascii=False, default=str, indent=2)

    content = f"""
[선택된 가설]: {state.get('selected_hypothesis', '미선택')}
[불량 증상]: {state.get('defect_description', '')}
[회사]: {state.get('company', '')}

[공정이력 데이터]
{fmt(state.get('process_history_result', []))}

[반송이력 데이터]
{fmt(state.get('return_history_result', []))}

[테스트결과 데이터]
{fmt(state.get('test_result', []))}
"""
    messages = [
        SystemMessage(content=SYNTHESIS_SYSTEM_PROMPT),
        HumanMessage(content=content),
    ]
    response = await llm.ainvoke(messages)
    return {"final_action_plan": response.content}
```

**Step 3: 커밋**

```bash
git add display_defect_chatbot/ai_server/agents/
git commit -m "feat(ai-server): 메인 분석 에이전트 및 종합 노드 추가"
```

---

## Task 9: LangGraph 그래프 (Send API 병렬)

**Files:**
- Create: `display_defect_chatbot/ai_server/agents/graph.py`

**Step 1: graph.py 작성**

```python
# display_defect_chatbot/ai_server/agents/graph.py
"""
LangGraph Send API 병렬 서브에이전트 그래프

흐름: entry → [Send API 병렬 팬아웃] → 4개 서브에이전트 → synthesis → END
"""
import operator
from typing import Annotated, TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.memory import InMemorySaver

from ai_server.agents.sub.process_history import process_history_node
from ai_server.agents.sub.return_history import return_history_node
from ai_server.agents.sub.test_result import test_result_node
from ai_server.agents.sub.long_term import long_term_node
from ai_server.agents.synthesis_node import synthesis_node


class DefectAnalysisState(TypedDict):
    # 입력
    company: str
    defect_description: str
    product_id: str
    selected_hypothesis: str
    session_id: str

    # 병렬 서브에이전트 결과 (operator.add로 합산)
    process_history_result: Annotated[list, operator.add]
    return_history_result: Annotated[list, operator.add]
    test_result: Annotated[list, operator.add]
    long_term_task_id: Annotated[list, operator.add]

    # 최종 출력
    final_action_plan: str


def route_to_agents(state: DefectAnalysisState) -> list[Send]:
    """Send API: 4개 서브에이전트로 병렬 팬아웃"""
    sub_state = dict(state)
    return [
        Send("process_history_node", sub_state),
        Send("return_history_node", sub_state),
        Send("test_result_node", sub_state),
        Send("long_term_node", sub_state),
    ]


def build_investigation_graph():
    builder = StateGraph(DefectAnalysisState)

    builder.add_node("process_history_node", process_history_node)
    builder.add_node("return_history_node", return_history_node)
    builder.add_node("test_result_node", test_result_node)
    builder.add_node("long_term_node", long_term_node)
    builder.add_node("synthesis", synthesis_node)

    # START → Send API 병렬 팬아웃
    builder.add_conditional_edges(START, route_to_agents)

    # 각 서브에이전트 → synthesis (LangGraph가 모두 완료될 때까지 대기)
    builder.add_edge("process_history_node", "synthesis")
    builder.add_edge("return_history_node", "synthesis")
    builder.add_edge("test_result_node", "synthesis")
    builder.add_edge("long_term_node", "synthesis")

    builder.add_edge("synthesis", END)

    checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)


# 앱 시작 시 단일 인스턴스 생성
investigation_graph = build_investigation_graph()
```

**Step 2: 커밋**

```bash
git add display_defect_chatbot/ai_server/agents/graph.py
git commit -m "feat(ai-server): LangGraph Send API 병렬 서브에이전트 그래프 추가"
```

---

## Task 10: FastAPI server.py

**Files:**
- Create: `display_defect_chatbot/ai_server/server.py`

**Step 1: server.py 작성**

```python
# display_defect_chatbot/ai_server/server.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
import os
import tempfile

from ai_server.config import get_settings
from ai_server.infra.vector_store import VectorStoreManager
from ai_server.infra.ingest import ingest_document
from ai_server.infra.tracing import setup_tracing
from ai_server.infra.database import get_db_session
from ai_server.agents.main_agent import run_main_analysis
from ai_server.agents.graph import investigation_graph, DefectAnalysisState
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import text

settings = get_settings()
app = FastAPI(title="Defect AI Server")

vsm: Optional[VectorStoreManager] = None


@app.on_event("startup")
async def startup():
    global vsm
    setup_tracing(settings.phoenix_collector_endpoint)
    embedding = OpenAIEmbeddings(model=settings.embedding_model)
    vsm = await VectorStoreManager.create(settings.pg_async_url, embedding)


# ── Request/Response Models ──────────────────────────────────

class AnalyzeRequest(BaseModel):
    session_id: str
    company: str
    defect_description: str


class AnalyzeResponse(BaseModel):
    session_id: str
    hypotheses: list[str]


class InvestigateRequest(BaseModel):
    session_id: str
    company: str
    defect_description: str
    product_id: str
    selected_hypothesis: str


class InvestigateResponse(BaseModel):
    action_plan: str
    process_history: list
    return_history: list
    test_results: list
    long_term_task_id: Optional[str]


class BgStatusResponse(BaseModel):
    task_id: str
    status: str
    result_text: Optional[str]


# ── Endpoints ──────────────────────────────────────────────

@app.post("/internal/analyze", response_model=AnalyzeResponse)
async def analyze_defect(req: AnalyzeRequest):
    """1단계: RAG로 불량 원인 가설 생성"""
    hypotheses = await run_main_analysis(req.defect_description, req.company, vsm)
    return AnalyzeResponse(session_id=req.session_id, hypotheses=hypotheses)


@app.post("/internal/investigate", response_model=InvestigateResponse)
async def investigate_defect(req: InvestigateRequest):
    """2단계: 가설 선택 후 Send API 병렬 서브에이전트 실행"""
    config = {"configurable": {"thread_id": req.session_id}}
    initial_state: DefectAnalysisState = {
        "company": req.company,
        "defect_description": req.defect_description,
        "product_id": req.product_id,
        "selected_hypothesis": req.selected_hypothesis,
        "session_id": req.session_id,
        "process_history_result": [],
        "return_history_result": [],
        "test_result": [],
        "long_term_task_id": [],
        "final_action_plan": "",
    }
    state = await investigation_graph.ainvoke(initial_state, config=config)

    task_ids = state.get("long_term_task_id", [])
    return InvestigateResponse(
        action_plan=state.get("final_action_plan", ""),
        process_history=state.get("process_history_result", []),
        return_history=state.get("return_history_result", []),
        test_results=state.get("test_result", []),
        long_term_task_id=task_ids[0] if task_ids else None,
    )


@app.get("/internal/bg-status/{task_id}", response_model=BgStatusResponse)
async def get_bg_status(task_id: str):
    """백그라운드 장기이력 분석 완료 상태 조회"""
    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT task_id, status, result_text FROM background_tasks WHERE task_id = :tid"),
            {"tid": task_id},
        )
        row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return BgStatusResponse(**dict(row))


@app.post("/internal/ingest")
async def ingest(doc_id: str, file: UploadFile = File(...)):
    """txt 문서를 PGVector에 색인"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        count = await ingest_document(doc_id, tmp_path, vsm)
        return {"doc_id": doc_id, "chunks": count}
    finally:
        os.unlink(tmp_path)


@app.delete("/internal/delete/{doc_id}")
async def delete_document(doc_id: str):
    deleted = await vsm.delete_by_doc_id(doc_id)
    return {"doc_id": doc_id, "deleted_chunks": deleted}


@app.get("/internal/health")
async def health():
    return {"status": "ok"}
```

**Step 2: 로컬 검증 (Docker 필요)**

```bash
cd display_defect_chatbot
docker compose up postgres ai-server -d
# 잠시 후
curl http://localhost:8001/internal/health
# Expected: {"status":"ok"}
```

**Step 3: 커밋**

```bash
git add display_defect_chatbot/ai_server/server.py
git commit -m "feat(ai-server): FastAPI server.py (analyze, investigate, bg-status 엔드포인트) 추가"
```

---

## Task 11: Spring Boot 스캐폴딩

**Files:**
- Create: `display_defect_chatbot/backend/pom.xml`
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/ChatbotApplication.java`
- Create: `display_defect_chatbot/backend/src/main/resources/application.properties`
- Create: `display_defect_chatbot/backend/Dockerfile`

**Step 1: pom.xml (ncs_rag_chatbot 기반, Oracle/Redis 제거)**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>4.0.2</version>
    <relativePath/>
  </parent>

  <groupId>com.sdi</groupId>
  <artifactId>chatbot</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <name>display-defect-chatbot</name>

  <properties>
    <java.version>17</java.version>
  </properties>

  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-webmvc</artifactId>
    </dependency>
    <dependency>
      <groupId>org.mybatis.spring.boot</groupId>
      <artifactId>mybatis-spring-boot-starter</artifactId>
      <version>4.0.1</version>
    </dependency>
    <dependency>
      <groupId>org.postgresql</groupId>
      <artifactId>postgresql</artifactId>
      <scope>runtime</scope>
    </dependency>
    <dependency>
      <groupId>org.projectlombok</groupId>
      <artifactId>lombok</artifactId>
      <optional>true</optional>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-webmvc-test</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <configuration>
          <annotationProcessorPaths>
            <path>
              <groupId>org.projectlombok</groupId>
              <artifactId>lombok</artifactId>
            </path>
          </annotationProcessorPaths>
        </configuration>
      </plugin>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
        <configuration>
          <excludes>
            <exclude>
              <groupId>org.projectlombok</groupId>
              <artifactId>lombok</artifactId>
            </exclude>
          </excludes>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
```

**Step 2: ChatbotApplication.java**

```java
// display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/ChatbotApplication.java
package com.sdi.chatbot;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.sdi.chatbot.mapper")
public class ChatbotApplication {
    public static void main(String[] args) {
        SpringApplication.run(ChatbotApplication.class, args);
    }
}
```

**Step 3: application.properties**

```properties
# display_defect_chatbot/backend/src/main/resources/application.properties
server.port=8080

# PostgreSQL
spring.datasource.url=jdbc:postgresql://${POSTGRES_HOST:localhost}:${POSTGRES_PORT:5432}/${POSTGRES_DB:defect_db}
spring.datasource.username=${POSTGRES_USER:postgres}
spring.datasource.password=${POSTGRES_PASSWORD:1234}
spring.datasource.driver-class-name=org.postgresql.Driver

# MyBatis
mybatis.mapper-locations=classpath:mapper/*.xml
mybatis.configuration.map-underscore-to-camel-case=true

# AI Server
ai.server.url=${INTERNAL_AI_SERVER_URL:http://localhost:8000}

# CORS
spring.web.resources.add-mappings=false
logging.level.com.sdi=DEBUG
```

**Step 4: Dockerfile (ncs_rag_chatbot 패턴 참조)**

```dockerfile
# display_defect_chatbot/backend/Dockerfile
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn package -DskipTests -B

FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]
```

**Step 5: 커밋**

```bash
git add display_defect_chatbot/backend/
git commit -m "feat(backend): Spring Boot 프로젝트 스캐폴딩 (pom.xml, application.properties)"
```

---

## Task 12: Spring Boot 도메인 레이어

**Files:**
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/model/Document.java`
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/dto/AnalyzeRequest.java`
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/dto/AnalyzeResponse.java`
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/dto/InvestigateRequest.java`
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/dto/InvestigateResponse.java`
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/mapper/DocumentMapper.java`
- Create: `display_defect_chatbot/backend/src/main/resources/mapper/DocumentMapper.xml`

**Step 1: Document.java**

```java
package com.sdi.chatbot.model;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class Document {
    private String docId;
    private String filename;
    private String docType;
    private String status;
    private LocalDateTime createdAt;
}
```

**Step 2: DTO 클래스들**

```java
// AnalyzeRequest.java
package com.sdi.chatbot.dto;
import lombok.Data;

@Data
public class AnalyzeRequest {
    private String sessionId;
    private String company;
    private String defectDescription;
}
```

```java
// AnalyzeResponse.java
package com.sdi.chatbot.dto;
import lombok.Data;
import java.util.List;

@Data
public class AnalyzeResponse {
    private String sessionId;
    private List<String> hypotheses;
}
```

```java
// InvestigateRequest.java
package com.sdi.chatbot.dto;
import lombok.Data;

@Data
public class InvestigateRequest {
    private String sessionId;
    private String company;
    private String defectDescription;
    private String productId;
    private String selectedHypothesis;
}
```

```java
// InvestigateResponse.java
package com.sdi.chatbot.dto;
import lombok.Data;
import java.util.List;

@Data
public class InvestigateResponse {
    private String actionPlan;
    private List<Object> processHistory;
    private List<Object> returnHistory;
    private List<Object> testResults;
    private String longTermTaskId;
}
```

**Step 3: DocumentMapper.java**

```java
package com.sdi.chatbot.mapper;

import com.sdi.chatbot.model.Document;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;

@Mapper
public interface DocumentMapper {
    List<Document> findAll();
    void insert(Document document);
    void deleteByDocId(String docId);
    void updateStatus(String docId, String status);
}
```

**Step 4: DocumentMapper.xml**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
    "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.sdi.chatbot.mapper.DocumentMapper">

  <select id="findAll" resultType="com.sdi.chatbot.model.Document">
    SELECT doc_id, filename, doc_type, status, created_at
    FROM documents
    ORDER BY created_at DESC
  </select>

  <insert id="insert">
    INSERT INTO documents (doc_id, filename, doc_type, status)
    VALUES (#{docId}, #{filename}, #{docType}, #{status})
  </insert>

  <delete id="deleteByDocId">
    DELETE FROM documents WHERE doc_id = #{docId}
  </delete>

  <update id="updateStatus">
    UPDATE documents SET status = #{status} WHERE doc_id = #{docId}
  </update>

</mapper>
```

**Step 5: 커밋**

```bash
git add display_defect_chatbot/backend/
git commit -m "feat(backend): 도메인 모델, DTO, MyBatis 매퍼 추가"
```

---

## Task 13: Spring Boot 서비스 + 컨트롤러

**Files:**
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/config/CorsConfig.java`
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/config/RestClientConfig.java`
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/service/ChatService.java`
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/service/DocumentService.java`
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/controller/ChatController.java`
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/controller/DocumentController.java`
- Create: `display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/controller/SessionController.java`

**Step 1: CorsConfig.java**

```java
package com.sdi.chatbot.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class CorsConfig {
    @Bean
    public WebMvcConfigurer corsConfigurer() {
        return new WebMvcConfigurer() {
            @Override
            public void addCorsMappings(CorsRegistry registry) {
                registry.addMapping("/api/**")
                        .allowedOrigins("*")
                        .allowedMethods("GET", "POST", "DELETE", "PUT");
            }
        };
    }
}
```

**Step 2: RestClientConfig.java**

```java
package com.sdi.chatbot.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
public class RestClientConfig {

    @Value("${ai.server.url}")
    private String aiServerUrl;

    @Bean
    public RestClient aiRestClient() {
        return RestClient.builder()
                .baseUrl(aiServerUrl)
                .build();
    }
}
```

**Step 3: ChatService.java**

```java
package com.sdi.chatbot.service;

import com.sdi.chatbot.dto.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
@RequiredArgsConstructor
public class ChatService {

    private final RestClient aiRestClient;

    public AnalyzeResponse analyze(AnalyzeRequest request) {
        return aiRestClient.post()
                .uri("/internal/analyze")
                .body(request)
                .retrieve()
                .body(AnalyzeResponse.class);
    }

    public InvestigateResponse investigate(InvestigateRequest request) {
        return aiRestClient.post()
                .uri("/internal/investigate")
                .body(request)
                .retrieve()
                .body(InvestigateResponse.class);
    }

    public Object getBgStatus(String taskId) {
        return aiRestClient.get()
                .uri("/internal/bg-status/" + taskId)
                .retrieve()
                .body(Object.class);
    }
}
```

**Step 4: DocumentService.java**

```java
package com.sdi.chatbot.service;

import com.sdi.chatbot.mapper.DocumentMapper;
import com.sdi.chatbot.model.Document;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentMapper documentMapper;
    private final RestClient aiRestClient;

    public List<Document> findAll() {
        return documentMapper.findAll();
    }

    public Document upload(MultipartFile file) throws Exception {
        String docId = UUID.randomUUID().toString();

        // AI 서버에 색인 요청
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new ByteArrayResource(file.getBytes()) {
            @Override public String getFilename() { return file.getOriginalFilename(); }
        });
        aiRestClient.post()
                .uri("/internal/ingest?doc_id=" + docId)
                .body(body)
                .retrieve()
                .toBodilessEntity();

        // DB 등록
        Document doc = new Document();
        doc.setDocId(docId);
        doc.setFilename(file.getOriginalFilename());
        doc.setDocType("txt");
        doc.setStatus("INDEXED");
        documentMapper.insert(doc);
        return doc;
    }

    public void delete(String docId) {
        aiRestClient.delete()
                .uri("/internal/delete/" + docId)
                .retrieve()
                .toBodilessEntity();
        documentMapper.deleteByDocId(docId);
    }
}
```

**Step 5: ChatController.java**

```java
package com.sdi.chatbot.controller;

import com.sdi.chatbot.dto.*;
import com.sdi.chatbot.service.ChatService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;

    @PostMapping("/analyze")
    public ResponseEntity<AnalyzeResponse> analyze(@RequestBody AnalyzeRequest request) {
        return ResponseEntity.ok(chatService.analyze(request));
    }

    @PostMapping("/investigate")
    public ResponseEntity<InvestigateResponse> investigate(@RequestBody InvestigateRequest request) {
        return ResponseEntity.ok(chatService.investigate(request));
    }
}
```

**Step 6: DocumentController.java**

```java
package com.sdi.chatbot.controller;

import com.sdi.chatbot.model.Document;
import com.sdi.chatbot.service.DocumentService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;

    @GetMapping
    public ResponseEntity<List<Document>> list() {
        return ResponseEntity.ok(documentService.findAll());
    }

    @PostMapping
    public ResponseEntity<Document> upload(@RequestParam("file") MultipartFile file) throws Exception {
        return ResponseEntity.ok(documentService.upload(file));
    }

    @DeleteMapping("/{docId}")
    public ResponseEntity<Void> delete(@PathVariable String docId) {
        documentService.delete(docId);
        return ResponseEntity.noContent().build();
    }
}
```

**Step 7: SessionController.java (백그라운드 작업 상태 폴링)**

```java
package com.sdi.chatbot.controller;

import com.sdi.chatbot.service.ChatService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/sessions")
@RequiredArgsConstructor
public class SessionController {

    private final ChatService chatService;

    @GetMapping("/bg-status/{taskId}")
    public ResponseEntity<Object> getBgStatus(@PathVariable String taskId) {
        return ResponseEntity.ok(chatService.getBgStatus(taskId));
    }
}
```

**Step 8: 커밋**

```bash
git add display_defect_chatbot/backend/
git commit -m "feat(backend): Spring Boot 서비스 및 컨트롤러 추가 (Chat, Document, Session)"
```

---

## Task 14: Vue.js 프론트엔드 스캐폴딩

**Files:**
- Create: `display_defect_chatbot/frontend/package.json`
- Create: `display_defect_chatbot/frontend/vite.config.js`
- Create: `display_defect_chatbot/frontend/index.html`
- Create: `display_defect_chatbot/frontend/src/main.js`
- Create: `display_defect_chatbot/frontend/src/App.vue`
- Create: `display_defect_chatbot/frontend/src/api/defectApi.js`
- Create: `display_defect_chatbot/frontend/src/composables/useDefectChat.js`

**Step 1: package.json**

```json
{
  "name": "display-defect-chatbot",
  "version": "0.0.1",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.5.0",
    "marked": "^12.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

**Step 2: vite.config.js**

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5174,
    proxy: {
      '/api': { target: 'http://backend:8080', changeOrigin: true }
    }
  }
})
```

**Step 3: index.html**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <title>Display Defect Chatbot</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #e0e0e0; }
  </style>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

**Step 4: main.js**

```js
import { createApp } from 'vue'
import App from './App.vue'
createApp(App).mount('#app')
```

**Step 5: defectApi.js**

```js
// display_defect_chatbot/frontend/src/api/defectApi.js
const BASE = '/api'

export async function analyzeDefect({ sessionId, company, defectDescription }) {
  const res = await fetch(`${BASE}/chat/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId, company, defectDescription })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function investigateDefect({ sessionId, company, defectDescription, productId, selectedHypothesis }) {
  const res = await fetch(`${BASE}/chat/investigate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId, company, defectDescription, productId, selectedHypothesis })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getBgStatus(taskId) {
  const res = await fetch(`${BASE}/sessions/bg-status/${taskId}`)
  return res.json()
}

export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/documents`, { method: 'POST', body: form })
  return res.json()
}

export async function fetchDocuments() {
  const res = await fetch(`${BASE}/documents`)
  return res.json()
}

export async function deleteDocument(docId) {
  await fetch(`${BASE}/documents/${docId}`, { method: 'DELETE' })
}
```

**Step 6: useDefectChat.js**

```js
// display_defect_chatbot/frontend/src/composables/useDefectChat.js
import { ref, reactive } from 'vue'
import { analyzeDefect, investigateDefect, getBgStatus } from '../api/defectApi.js'
import { v4 as uuidv4 } from 'uuid'

export function useDefectChat() {
  const sessionId = ref(uuidv4())
  const step = ref('input')  // input | hypotheses | investigating | result
  const loading = ref(false)
  const error = ref(null)

  const form = reactive({ company: '', defectDescription: '', productId: '' })
  const hypotheses = ref([])
  const selectedHypothesis = ref('')
  const result = reactive({
    actionPlan: '',
    processHistory: [],
    returnHistory: [],
    testResults: [],
    longTermTaskId: null,
    longTermStatus: 'PENDING',
    longTermResult: null,
  })

  async function analyze() {
    loading.value = true
    error.value = null
    try {
      const data = await analyzeDefect({
        sessionId: sessionId.value,
        company: form.company,
        defectDescription: form.defectDescription,
      })
      hypotheses.value = data.hypotheses
      step.value = 'hypotheses'
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function investigate(hypothesis) {
    selectedHypothesis.value = hypothesis
    loading.value = true
    step.value = 'investigating'
    try {
      const data = await investigateDefect({
        sessionId: sessionId.value,
        company: form.company,
        defectDescription: form.defectDescription,
        productId: form.productId,
        selectedHypothesis: hypothesis,
      })
      result.actionPlan = data.actionPlan
      result.processHistory = data.processHistory || []
      result.returnHistory = data.returnHistory || []
      result.testResults = data.testResults || []
      result.longTermTaskId = data.longTermTaskId
      step.value = 'result'

      if (data.longTermTaskId) {
        pollBgStatus(data.longTermTaskId)
      }
    } catch (e) {
      error.value = e.message
      step.value = 'hypotheses'
    } finally {
      loading.value = false
    }
  }

  function pollBgStatus(taskId) {
    const timer = setInterval(async () => {
      const data = await getBgStatus(taskId)
      result.longTermStatus = data.status
      if (data.status === 'COMPLETED' || data.status === 'FAILED') {
        result.longTermResult = data.resultText
        clearInterval(timer)
      }
    }, 3000)
  }

  function reset() {
    sessionId.value = uuidv4()
    step.value = 'input'
    hypotheses.value = []
    selectedHypothesis.value = ''
    Object.assign(result, {
      actionPlan: '', processHistory: [], returnHistory: [], testResults: [],
      longTermTaskId: null, longTermStatus: 'PENDING', longTermResult: null,
    })
  }

  return { sessionId, step, loading, error, form, hypotheses, selectedHypothesis, result, analyze, investigate, reset }
}
```

**Step 7: 커밋**

```bash
git add display_defect_chatbot/frontend/
git commit -m "feat(frontend): Vue.js 스캐폴딩 및 API/composable 추가"
```

---

## Task 15: Vue.js 컴포넌트

**Files:**
- Create: `display_defect_chatbot/frontend/src/App.vue`
- Create: `display_defect_chatbot/frontend/src/components/InputView.vue`
- Create: `display_defect_chatbot/frontend/src/components/HypothesisSelector.vue`
- Create: `display_defect_chatbot/frontend/src/components/AgentResultPanel.vue`
- Create: `display_defect_chatbot/frontend/src/components/BgTaskNotifier.vue`

**Step 1: App.vue**

```vue
<template>
  <div class="app">
    <header class="header">
      <h1>🔬 Display Defect Analyzer</h1>
      <span class="subtitle">삼성 디스플레이 픽셀 불량 분석 AI</span>
      <button v-if="step !== 'input'" @click="reset" class="btn-reset">새 분석 시작</button>
    </header>

    <main class="main">
      <InputView v-if="step === 'input'" :form="form" :loading="loading" :error="error" @analyze="analyze" />
      <HypothesisSelector v-if="step === 'hypotheses'" :hypotheses="hypotheses" :loading="loading" @select="investigate" />
      <div v-if="step === 'investigating'" class="investigating">
        <div class="spinner"></div>
        <p>병렬 분석 중... 공정이력, 반송이력, 테스트결과를 동시에 조회하고 있습니다.</p>
      </div>
      <AgentResultPanel v-if="step === 'result'" :result="result" :hypothesis="selectedHypothesis" />
    </main>

    <BgTaskNotifier v-if="result.longTermTaskId" :status="result.longTermStatus" :result-text="result.longTermResult" />
  </div>
</template>

<script setup>
import { useDefectChat } from './composables/useDefectChat.js'
import InputView from './components/InputView.vue'
import HypothesisSelector from './components/HypothesisSelector.vue'
import AgentResultPanel from './components/AgentResultPanel.vue'
import BgTaskNotifier from './components/BgTaskNotifier.vue'

const { step, loading, error, form, hypotheses, selectedHypothesis, result, analyze, investigate, reset } = useDefectChat()
</script>

<style>
.app { display: flex; flex-direction: column; min-height: 100vh; }
.header { background: #1a1d27; padding: 16px 24px; display: flex; align-items: center; gap: 16px; border-bottom: 1px solid #2a2d3a; }
.header h1 { font-size: 1.3rem; color: #60a5fa; }
.subtitle { color: #6b7280; font-size: 0.85rem; }
.btn-reset { margin-left: auto; background: #374151; color: #e0e0e0; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; }
.main { flex: 1; padding: 24px; max-width: 1200px; margin: 0 auto; width: 100%; }
.investigating { text-align: center; padding: 60px; color: #9ca3af; }
.spinner { width: 40px; height: 40px; border: 3px solid #374151; border-top-color: #60a5fa; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 16px; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
```

**Step 2: InputView.vue**

```vue
<template>
  <div class="input-view">
    <h2>불량 정보 입력</h2>
    <div class="form">
      <label>보고 회사</label>
      <input v-model="form.company" placeholder="예: A사" />
      <label>불량 증상 설명</label>
      <textarea v-model="form.defectDescription" rows="4"
        placeholder="예: 화면 좌측 상단 픽셀 10개가 완전히 꺼져 있음 (Dead Pixel)"></textarea>
      <label>제품 ID / Lot No</label>
      <input v-model="form.productId" placeholder="예: LOT-A001" />
      <button @click="$emit('analyze')" :disabled="loading || !form.defectDescription">
        {{ loading ? '분석 중...' : '원인 분석 시작' }}
      </button>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps(['form', 'loading', 'error'])
defineEmits(['analyze'])
</script>

<style scoped>
.input-view { max-width: 600px; margin: 40px auto; }
h2 { color: #60a5fa; margin-bottom: 24px; }
.form { display: flex; flex-direction: column; gap: 12px; }
label { color: #9ca3af; font-size: 0.85rem; }
input, textarea { background: #1e2130; border: 1px solid #374151; border-radius: 8px; padding: 10px 14px; color: #e0e0e0; font-size: 0.95rem; width: 100%; }
button { background: #2563eb; color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-size: 1rem; margin-top: 8px; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
.error { color: #f87171; font-size: 0.85rem; }
</style>
```

**Step 3: HypothesisSelector.vue**

```vue
<template>
  <div class="hypothesis-view">
    <h2>원인 가설 선택</h2>
    <p class="hint">AI가 과거 사례를 기반으로 생성한 가설입니다. 가장 적합한 것을 선택하세요.</p>
    <div class="hypotheses">
      <button
        v-for="(h, i) in hypotheses"
        :key="i"
        class="hypothesis-btn"
        :disabled="loading"
        @click="$emit('select', h)"
      >
        {{ h }}
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps(['hypotheses', 'loading'])
defineEmits(['select'])
</script>

<style scoped>
.hypothesis-view { max-width: 700px; margin: 40px auto; }
h2 { color: #60a5fa; margin-bottom: 8px; }
.hint { color: #6b7280; font-size: 0.85rem; margin-bottom: 24px; }
.hypotheses { display: flex; flex-direction: column; gap: 12px; }
.hypothesis-btn {
  background: #1e2130; border: 1px solid #3b4fd0; border-radius: 10px;
  padding: 16px 20px; color: #e0e0e0; text-align: left; cursor: pointer; font-size: 0.95rem;
  transition: background 0.2s;
}
.hypothesis-btn:hover { background: #2a305a; border-color: #60a5fa; }
</style>
```

**Step 4: AgentResultPanel.vue**

```vue
<template>
  <div class="result-view">
    <div class="hypothesis-badge">선택된 가설: {{ hypothesis }}</div>

    <!-- 서브에이전트 결과 그리드 -->
    <div class="agent-grid">
      <div class="agent-card">
        <h3>⚙️ 공정이력</h3>
        <table v-if="result.processHistory.length">
          <tr v-for="(r, i) in result.processHistory" :key="i">
            <td>{{ r.process_step }}</td>
            <td :class="r.result">{{ r.result }}</td>
            <td>{{ r.equipment_id }}</td>
          </tr>
        </table>
        <p v-else class="empty">데이터 없음</p>
      </div>

      <div class="agent-card">
        <h3>↩️ 반송이력</h3>
        <table v-if="result.returnHistory.length">
          <tr v-for="(r, i) in result.returnHistory" :key="i">
            <td>{{ r.return_reason }}</td>
            <td :class="r.severity?.toLowerCase()">{{ r.severity }}</td>
            <td>{{ r.quantity }}건</td>
          </tr>
        </table>
        <p v-else class="empty">데이터 없음</p>
      </div>

      <div class="agent-card">
        <h3>🧪 테스트결과</h3>
        <table v-if="result.testResults.length">
          <tr v-for="(r, i) in result.testResults" :key="i">
            <td>{{ r.test_type }}</td>
            <td :class="r.result">{{ r.result }}</td>
            <td>{{ r.measured_value }}</td>
          </tr>
        </table>
        <p v-else class="empty">데이터 없음</p>
      </div>

      <div class="agent-card long-term">
        <h3>📊 장기이력 분석 <span class="badge" :class="result.longTermStatus">{{ result.longTermStatus }}</span></h3>
        <pre v-if="result.longTermResult">{{ result.longTermResult }}</pre>
        <p v-else class="empty">백그라운드 분석 진행 중...</p>
      </div>
    </div>

    <!-- 최종 조치안 -->
    <div class="action-plan">
      <h3>📋 최종 조치 방안</h3>
      <div v-html="renderedPlan" class="plan-content"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps(['result', 'hypothesis'])
const renderedPlan = computed(() => marked(props.result.actionPlan || ''))
</script>

<style scoped>
.result-view { display: flex; flex-direction: column; gap: 24px; }
.hypothesis-badge { background: #1e3a5f; border: 1px solid #3b82f6; border-radius: 8px; padding: 10px 16px; color: #93c5fd; font-size: 0.9rem; }
.agent-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.agent-card { background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 10px; padding: 16px; }
.agent-card h3 { color: #60a5fa; font-size: 0.9rem; margin-bottom: 12px; }
.long-term { grid-column: 1 / -1; }
table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
td { padding: 4px 8px; border-bottom: 1px solid #1e2130; }
.FAIL, .fail { color: #f87171; }
.PASS, .pass { color: #4ade80; }
.WARN, .warn, .medium { color: #fbbf24; }
.HIGH, .high { color: #f87171; }
.LOW, .low { color: #4ade80; }
.empty { color: #4b5563; font-size: 0.85rem; }
pre { font-size: 0.8rem; white-space: pre-wrap; color: #d1d5db; }
.badge { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; margin-left: 8px; }
.badge.PENDING { background: #374151; }
.badge.COMPLETED { background: #065f46; color: #6ee7b7; }
.badge.FAILED { background: #7f1d1d; color: #fca5a5; }
.action-plan { background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 10px; padding: 20px; }
.action-plan h3 { color: #60a5fa; margin-bottom: 16px; }
.plan-content { color: #d1d5db; line-height: 1.7; }
</style>
```

**Step 5: BgTaskNotifier.vue**

```vue
<template>
  <div v-if="status === 'COMPLETED'" class="notifier">
    ✅ 장기이력 분석 완료! 결과가 분석 패널에 표시되었습니다.
  </div>
  <div v-else-if="status === 'FAILED'" class="notifier error">
    ❌ 장기이력 분석 실패
  </div>
</template>

<script setup>
defineProps(['status', 'resultText'])
</script>

<style scoped>
.notifier {
  position: fixed; bottom: 24px; right: 24px;
  background: #065f46; color: #6ee7b7; padding: 12px 20px;
  border-radius: 8px; font-size: 0.9rem; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.notifier.error { background: #7f1d1d; color: #fca5a5; }
</style>
```

**Step 6: 커밋**

```bash
git add display_defect_chatbot/frontend/
git commit -m "feat(frontend): Vue.js 컴포넌트 추가 (InputView, HypothesisSelector, AgentResultPanel, BgTaskNotifier)"
```

---

## Task 16: Docker Compose 통합 실행 검증

**Step 1: Mock 문서를 AI 서버에 색인**

```bash
# 모든 서비스 기동
cd display_defect_chatbot
docker compose up -d --build

# 잠시 후 헬스 확인
curl http://localhost:8001/internal/health
# Expected: {"status":"ok"}

curl http://localhost:8081/api/documents
# Expected: []
```

**Step 2: Mock txt 파일 업로드**

```bash
# pixel_failure_cases.txt 업로드 (Spring을 통해)
curl -X POST http://localhost:8081/api/documents \
  -F "file=@ai_server/mock_data/pixel_failure_cases.txt"

curl -X POST http://localhost:8081/api/documents \
  -F "file=@ai_server/mock_data/process_sop.txt"

# 확인
curl http://localhost:8081/api/documents
# Expected: 2개 문서, status: INDEXED
```

**Step 3: 분석 플로우 E2E 검증**

```bash
# 1단계: 가설 생성
curl -X POST http://localhost:8081/api/chat/analyze \
  -H "Content-Type: application/json" \
  -d '{"sessionId":"test-001","company":"A사","defectDescription":"화면 좌측 픽셀 10개 완전 소등"}'
# Expected: {"sessionId":"test-001","hypotheses":["가설1: ...","가설2: ..."]}

# 2단계: 병렬 조사
curl -X POST http://localhost:8081/api/chat/investigate \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId":"test-001","company":"A사",
    "defectDescription":"화면 좌측 픽셀 10개 완전 소등",
    "productId":"LOT-A001",
    "selectedHypothesis":"가설1: TFT 게이트 전극 단락 — CVD 파티클 오염으로 인한 단락"
  }'
# Expected: actionPlan, processHistory(8건), returnHistory, testResults, longTermTaskId

# 3단계: 백그라운드 작업 상태 확인 (약 10초 후)
curl http://localhost:8081/api/sessions/bg-status/{longTermTaskId}
# Expected: {"taskId":"...","status":"COMPLETED","resultText":"[장기 이력 분석]..."}
```

**Step 4: 프론트엔드 확인**

브라우저에서 `http://localhost:5175` 접속

**Step 5: 최종 커밋**

```bash
git add display_defect_chatbot/
git commit -m "feat: display_defect_chatbot 초기 구현 완료

- FastAPI Send API 병렬 서브에이전트 (공정/반송/테스트/장기이력)
- LangGraph 병렬 팬아웃 그래프
- Spring Boot API 게이트웨이
- Vue.js 2단계 UI (가설 선택 → 결과 패널)"
```

---

## 구현 완료 기준

- [ ] `docker compose up` 후 모든 서비스 정상 기동
- [ ] txt 문서 업로드 후 PGVector 색인 성공
- [ ] `/api/chat/analyze` → 가설 2-3개 반환
- [ ] `/api/chat/investigate` → 3개 서브에이전트 결과 + 조치안 반환
- [ ] 약 10초 후 `/api/sessions/bg-status/{id}` → COMPLETED 상태
- [ ] 프론트엔드에서 전체 플로우 동작
