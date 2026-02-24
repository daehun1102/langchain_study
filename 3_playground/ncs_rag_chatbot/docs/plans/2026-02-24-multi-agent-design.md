# 멀티에이전트 시스템 설계 — Supervisor + RAG Agent + SQL Agent

**Date:** 2026-02-24
**Scope:** `ai_server/` 전체 구조 개편 + Oracle DB 스키마

---

## 목표

1. 기존 RAG Agent를 서브에이전트로 유지하면서 SQL Agent를 추가한다.
2. Supervisor Agent(NCS 관리 감독관)가 LLM 기반으로 두 서브에이전트를 라우팅한다.
3. 서브에이전트는 `create_agent`로 생성하고, Supervisor의 `@tool`로 래핑한다.
4. `ai_server/`의 파일 구조를 역할별로 분리하여 유지보수성과 버전 관리를 개선한다.
5. Oracle LMS DB용 테이블 DDL 및 더미 데이터 SQL을 작성한다.

---

## 1. 멀티에이전트 아키텍처

### 에이전트 역할

| 에이전트 | 역할 | Tools |
|---------|------|-------|
| **Supervisor** | NCS 관리 감독관. LLM이 쿼리를 분석하여 서브에이전트 라우팅 및 최종 답변 통합 | `call_rag_agent`, `call_sql_agent` |
| **RAG Agent** | NCS 문서 전문가. PGVector에서 관련 문서 검색 후 답변 | `retrieve_context` |
| **SQL Agent** | 직원 이력 조회 전문가. Spring API를 통해 Oracle LMS DB 조회 | `query_employee_data` |

### 호출 흐름

```
POST /internal/chat {query, doc_ids, thread_id}
  └→ SupervisorAgent.run(query, config)
       ├→ [사번/이름 포함 시] call_sql_agent(query)
       │    └→ SqlAgent → query_employee_data(employee_id)
       │         └→ httpx → Spring GET /internal/v1/employee/history
       │              └→ Oracle LMS DB 조회 결과 반환
       │
       ├→ [NCS 문서 검색 필요 시] call_rag_agent(query + sql_context)
       │    └→ RagAgent → retrieve_context() → PGVector
       │         └→ NCS 문서 내용 반환
       │
       └→ Supervisor: 결과 통합 → 최종 답변
```

### 라우팅 전략 (LLM 기반, 순차 처리)

Supervisor system prompt에 다음 지침을 명시한다:
- 사번 또는 직원 이름이 포함된 질문 → `call_sql_agent` 먼저 호출
- NCS 기준/문서 검색이 필요한 질문 → `call_rag_agent` 호출
- 둘 다 필요한 경우 → `call_sql_agent` 먼저, 결과를 컨텍스트에 포함하여 `call_rag_agent` 호출
- 두 결과를 통합하여 최종 답변 생성

### 서브에이전트 패턴

```python
# 서브에이전트를 @tool로 래핑하여 Supervisor에 등록
@tool
async def call_rag_agent(query: str) -> str:
    """NCS 문서에서 관련 내용을 검색하여 답변한다."""
    result = await rag_agent.run(query, config)
    return result.content

@tool
async def call_sql_agent(query: str) -> str:
    """직원의 교육 이수/과제/채점 이력을 조회하여 답변한다."""
    result = await sql_agent.run(query, config)
    return result.content

supervisor = SupervisorAgent(tools=[call_rag_agent, call_sql_agent])
```

---

## 2. 전체 파일 구조

```
ai_server/
  │
  ├── server.py                      # FastAPI 진입점
  ├── config.py                      # 환경변수 중앙 관리 (pydantic BaseSettings)
  │
  ├── agents/                        # 에이전트 (버전관리)
  │   ├── __init__.py                # 활성 버전 re-export
  │   ├── base.py                    # BaseAgent 추상 클래스
  │   └── v1/
  │       ├── __init__.py
  │       ├── rag_agent.py           # 기존 agent.py → 이동
  │       ├── sql_agent.py           # NEW
  │       └── supervisor.py          # NEW
  │
  ├── tools/                         # Tool 정의 (thin wrapper)
  │   ├── __init__.py
  │   ├── rag_tool.py                # 기존 tool.py → 이동
  │   └── sql_tool.py                # NEW: @tool 정의만, 호출은 clients에 위임
  │
  ├── clients/                       # 외부 API 클라이언트 (버전관리)
  │   ├── __init__.py
  │   └── spring/
  │       ├── __init__.py
  │       ├── base.py                # httpx AsyncClient 공통 설정 (base_url, timeout)
  │       └── v1/
  │           ├── __init__.py
  │           └── employee.py        # GET /internal/v1/employee/history
  │
  ├── infra/                         # 인프라 (기존 파일 그룹화)
  │   ├── __init__.py
  │   ├── embeddings.py              # 기존 이동
  │   ├── vector_store.py            # 기존 이동
  │   ├── prompt_loader.py           # 기존 이동
  │   └── tracing.py                 # 기존 이동
  │
  ├── eval/                          # 기존 유지
  ├── pytest.ini
  └── requirements.txt

db/
  ├── schema.sql                     # Oracle 4개 테이블 DDL
  └── dummy_data.sql                 # 더미 데이터 INSERT
```

### 버전 관리 전략

**에이전트 버전업 시:**
- `agents/v2/` 디렉토리 추가
- `agents/__init__.py`에서 import 경로 한 줄 교체

**Spring API 버전업 시:**
- `clients/spring/v2/employee.py` 추가
- `tools/sql_tool.py`의 import만 v1 → v2 교체

**의존 방향 (단방향):**
```
server.py
  └→ agents/v1/supervisor.py
       ├→ agents/v1/rag_agent.py  ←── tools/rag_tool.py   ←── infra/vector_store.py
       └→ agents/v1/sql_agent.py  ←── tools/sql_tool.py   ←── clients/spring/v1/employee.py
                                                                 └→ clients/spring/base.py
```

### config.py

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_connection: str = "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db"
    spring_base_url: str = "http://localhost:8080"
    redis_host: str = "localhost"
    redis_port: int = 6379
    model_name: str = "gpt-4o-mini"
    spring_api_version: str = "v1"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 3. Oracle DB 스키마

### 테이블 관계

```
TB_EMPLOYEE (직원 기본정보)
    │
    ├── TB_EDUCATION_HISTORY (교육 이수 내역)   1:N
    │
    ├── TB_ASSIGNMENT_SUBMISSION (과제 제출)    1:N
    │       │
    │       └── TB_GRADING_RESULT (채점 결과)  1:1
    │
    └── TB_GRADING_RESULT.GRADER_ID ──────────→ TB_EMPLOYEE (채점자)
```

### TB_EMPLOYEE — 직원 기본정보

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| EMPLOYEE_ID | VARCHAR2(20) | PK | 사번 |
| NAME | VARCHAR2(50) | NOT NULL | 이름 |
| DEPARTMENT | VARCHAR2(100) | NOT NULL | 부서 |
| POSITION | VARCHAR2(50) | | 직책 |
| JOIN_DATE | DATE | NOT NULL | 입사일 |
| EMAIL | VARCHAR2(100) | UNIQUE | 이메일 |
| CREATED_AT | DATE | DEFAULT SYSDATE | 등록일시 |

### TB_EDUCATION_HISTORY — 교육 이수 내역

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| HISTORY_ID | NUMBER | PK | 이수 ID (시퀀스) |
| EMPLOYEE_ID | VARCHAR2(20) | FK → TB_EMPLOYEE | 사번 |
| COURSE_NAME | VARCHAR2(200) | NOT NULL | 과정명 |
| NCS_CODE | VARCHAR2(50) | | NCS 분류 코드 |
| START_DATE | DATE | | 교육 시작일 |
| COMPLETION_DATE | DATE | | 이수 완료일 |
| STATUS | VARCHAR2(20) | NOT NULL | 완료/진행중/미이수 |
| SCORE | NUMBER(5,2) | | 이수 점수 |
| CREATED_AT | DATE | DEFAULT SYSDATE | 등록일시 |

### TB_ASSIGNMENT_SUBMISSION — 과제 제출

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| SUBMISSION_ID | NUMBER | PK | 제출 ID (시퀀스) |
| EMPLOYEE_ID | VARCHAR2(20) | FK → TB_EMPLOYEE | 사번 |
| COURSE_NAME | VARCHAR2(200) | NOT NULL | 과정명 |
| ASSIGNMENT_NAME | VARCHAR2(200) | NOT NULL | 과제명 |
| SUBMIT_DATE | DATE | | 제출일 |
| STATUS | VARCHAR2(20) | NOT NULL | 제출/미제출/반려 |
| FILE_PATH | VARCHAR2(500) | | 제출 파일 경로 |
| CREATED_AT | DATE | DEFAULT SYSDATE | 등록일시 |

### TB_GRADING_RESULT — 채점 결과

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| RESULT_ID | NUMBER | PK | 채점 ID (시퀀스) |
| SUBMISSION_ID | NUMBER | FK → TB_ASSIGNMENT_SUBMISSION | 제출 ID |
| EMPLOYEE_ID | VARCHAR2(20) | FK → TB_EMPLOYEE | 사번 |
| GRADER_ID | VARCHAR2(20) | FK → TB_EMPLOYEE | 채점자 사번 |
| SCORE | NUMBER(5,2) | | 점수 |
| PASS_YN | CHAR(1) | CHECK (Y/N) | 합격 여부 |
| FEEDBACK | VARCHAR2(4000) | | 피드백 |
| GRADED_DATE | DATE | | 채점일 |
| CREATED_AT | DATE | DEFAULT SYSDATE | 등록일시 |

---

## 4. Spring API 엔드포인트 (ai_server 호출용)

```
GET /internal/v1/employee/history?employeeId={id}
```

**응답 구조:**
```json
{
  "employee": {
    "employeeId": "EMP001",
    "name": "홍길동",
    "department": "개발팀",
    "position": "선임"
  },
  "educationHistory": [...],
  "assignmentSubmissions": [...],
  "gradingResults": [...]
}
```

---

## 5. 정책 결정 사항

| 항목 | 결정 |
|------|------|
| 서브에이전트 패턴 | `create_agent` + `@tool` 래핑 (subagents-as-tools) |
| 라우팅 방식 | LLM 기반, 순차 처리 (SQL → RAG) |
| Oracle DB 접근 | Spring API 호출 (ai_server는 직접 접근 안 함) |
| HTTP 클라이언트 | `httpx.AsyncClient` (clients/spring/base.py 공통 설정) |
| 에이전트 버전관리 | `agents/v1/`, `agents/v2/` 디렉토리 분리 |
| 클라이언트 버전관리 | `clients/spring/v1/`, `clients/spring/v2/` 디렉토리 분리 |
| 환경변수 관리 | `config.py` (pydantic BaseSettings) 중앙 집중 |
| 기존 인프라 파일 | `infra/` 디렉토리로 그룹화 |
| DB | Oracle LMS (4개 테이블 + 시퀀스) |
| 더미 데이터 | `db/dummy_data.sql` |
