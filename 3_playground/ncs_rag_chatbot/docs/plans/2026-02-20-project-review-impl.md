# NCS RAG Chatbot — 프로젝트 리뷰 작성 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 주니어 개발자가 NCS RAG Chatbot의 전체 기능 흐름을 코드 레벨로 단계적으로 이해할 수 있는 리뷰 문서를 작성한다.

**Architecture:** 시나리오 흐름 중심 — 전체 아키텍처 개요 → PDF 업로드 시나리오(11단계) → RAG 채팅 시나리오(12단계) → Redis 프롬프트 + Arize Phoenix 지원 시스템 순서로 작성한다. 각 단계마다 핵심 코드와 "왜 이렇게 했는지"를 설명한다.

**Tech Stack:** Spring Boot 4.0.2 / MyBatis / RestClient · Python FastAPI / LangGraph / langchain-postgres · Oracle DB / PostgreSQL+pgvector / Redis · Arize Phoenix · Vue.js 3 / Vite

---

## Task 1: 섹션 1 — 전체 아키텍처 개요 작성

**Files:**
- Create: `docs/plans/2026-02-20-project-review.md`

**Step 1: 서버 3개 분리 이유 설명**

다음 내용을 포함한다:
- Spring Boot(8080): 외부 공개 API Gateway. 파일 업로드, 인증, DB CRUD 등 "웹 서버" 역할. Java 생태계의 안정성 활용.
- Python FastAPI(8000): 순수 AI 추론 서버. 외부에 미노출, Spring만 호출. LangChain/LangGraph 등 AI 라이브러리는 Python 생태계가 압도적으로 풍부함.
- Vue.js(5174): 프론트엔드 SPA. Spring만 바라봄 (Python 직접 호출 없음).

**Step 2: 데이터베이스 분리 이유 설명**

다음 내용을 포함한다:
- Oracle: 문서 메타데이터 (파일명, 카테고리, 상태). 관계형 데이터에 적합.
- PGVector: 벡터 임베딩 저장. PostgreSQL 확장으로 SQL과 벡터 검색을 동시에.
- Redis: 시스템 프롬프트 저장. 재배포 없이 런타임 수정 가능.

**Step 3: doc_id 연결 구조 설명**

```
Oracle documents 테이블          PGVector ncs_vectors 테이블
┌─────────────────────────┐      ┌────────────────────────────┐
│ doc_id (UUID) ← PRIMARY │      │ doc_id (VARCHAR) ← FK 역할 │
│ filename                │  ←→  │ embedding (VECTOR)         │
│ main_category           │      │ page (INTEGER)             │
│ sub_category            │      │ content (TEXT)             │
│ status                  │      └────────────────────────────┘
└─────────────────────────┘
```

doc_id는 UUID이며, 두 DB를 연결하는 유일한 키다. PGVector는 Oracle을 참조하되 FK 제약은 없고 애플리케이션 레벨에서 일관성을 유지한다.

**Step 4: 전체 포트 맵 작성**

| 서버 | 포트 | 누가 호출하나 |
|------|------|-------------|
| Vue.js | 5174 | 브라우저 |
| Spring Boot | 8080 | Vue.js |
| Python FastAPI | 8000 | Spring만 |
| Oracle | 1521 | Spring만 |
| PGVector | 5432 | Python만 |
| Redis | 6379 | Spring + Python |
| Arize Phoenix | 6006/4317 | Python만 |

**Step 5: Commit**

```bash
git add docs/plans/2026-02-20-project-review.md
git commit -m "docs(review): 섹션 1 - 전체 아키텍처 개요"
```

---

## Task 2: 섹션 2 — 시나리오 1: PDF 업로드 흐름 작성

**Files:**
- Modify: `docs/plans/2026-02-20-project-review.md`

참고 파일:
- `frontend/src/components/DocumentView.vue`
- `frontend/src/api/ncsApi.js:41-53`
- `backend/.../controller/DocumentController.java`
- `backend/.../service/DocumentService.java`
- `ai_server/ingest.py`
- `ai_server/loader.py`
- `ai_server/splitter.py`
- `ai_server/embeddings.py`
- `ai_server/vector_store.py`
- `server.py:125-133`

**Step 1: 각 단계별 흐름 작성 (11단계)**

각 단계마다 다음 3가지를 포함:
- **무엇을 하는가** (한 문장 요약)
- **핵심 코드 스니펫** (핵심 메서드만 발췌, 5줄 이내)
- **왜 이렇게 했는가** (설계 의도 설명)

단계 목록:
1. 사용자가 파일을 선택하고 카테고리를 지정 (`DocumentView.vue`)
2. `ncsApi.js:uploadDocument()` — FormData 빌드 + `POST /api/documents`
3. `DocumentController.upload()` — `@RequestParam MultipartFile` 수신
4. `DocumentService.upload()` — UUID 발급 + 파일 저장 + Oracle INSERT (PENDING)
5. `DocumentMapper.insert()` — MyBatis XML `<insert>` 실행
6. `DocumentService`가 `RestClient.post("/internal/ingest")` 호출
7. `server.py:ingest()` — `IngestRequest(doc_id, file_path)` 수신
8. `ingest.py:ingest_single_document()` — 전체 파이프라인 진입점
9. `DocumentLoader.load()` → `DocumentSplitter.split_documents()` — PDF를 청크로 분할
10. `EmbeddingModel.get_embeddings()` + `PGVectorStore.aadd_documents()` — 임베딩 후 저장
11. Spring이 응답을 받아 `DocumentMapper.updateStatus(INDEXED)` 호출

**Step 2: 청크 분할 개념 설명 추가**

RecursiveCharacterTextSplitter의 chunk_size=1000, chunk_overlap=200의 의미를 시각적으로 설명:
```
[     1000자     ]
          [     1000자     ]
     ←200→ (overlap: 문맥 연속성 보장)
```

**Step 3: 메타데이터 흐름 설명**

각 청크에 `doc_id`와 `page`가 어떻게 붙는지:
```python
for doc in splits:
    doc.metadata["doc_id"] = doc_id   # Oracle과 연결
    doc.metadata["page"] = doc.metadata.get("page", 0)
```

**Step 4: 상태 전이 다이어그램**

```
업로드 시작 → PENDING (Oracle INSERT)
               ↓
         Python ingest 성공 → INDEXED
         Python ingest 실패 → FAILED
```

**Step 5: Commit**

```bash
git add docs/plans/2026-02-20-project-review.md
git commit -m "docs(review): 섹션 2 - PDF 업로드 시나리오"
```

---

## Task 3: 섹션 3 — 시나리오 2: RAG 채팅 흐름 작성

**Files:**
- Modify: `docs/plans/2026-02-20-project-review.md`

참고 파일:
- `frontend/src/components/ChatView.vue` + `ChatInput.vue`
- `frontend/src/api/ncsApi.js:17-33`
- `backend/.../controller/ChatController.java`
- `backend/.../service/ChatService.java`
- `backend/.../mapper/DocumentMapper.xml` (`findDocIdsByCategory`)
- `server.py:136-175`
- `ai_server/tool.py`
- `ai_server/agent.py`
- `ai_server/vector_store.py`

**Step 1: 각 단계별 흐름 작성 (12단계)**

각 단계마다 핵심 코드 + 설명:

1. 사용자가 채팅 입력창에 질문 + 카테고리 선택 (`ChatInput.vue`)
2. `ncsApi.js:sendChat(query, mainCategory, subCategory)` — `POST /api/chat`
3. `ChatController.chat()` — `@RequestBody ChatRequest` 수신
4. `ChatService.chat()` — 카테고리 조건으로 Oracle 조회 시작
5. `DocumentMapper.findDocIdsByCategory()` — `WHERE status='INDEXED' AND main_category=?` → doc_id 목록 반환
6. `RestClient.post("/internal/chat")` — `{query, doc_ids}` Python 전달
7. `server.py:chat()` — `ChatRequest(query, doc_ids)` 수신
8. `ToolBuilder.build_tools(doc_ids)` — doc_ids를 클로저로 캡처한 검색 도구 생성
9. `ChatAgent.create_agent(tools)` — LangGraph `create_react_agent()` 호출
10. `agent.run(query)` — ReAct 루프 시작 (Reason → Act → Observe)
11. `retrieve_context(query)` → `similarity_search_by_doc_ids()` — `doc_id IN (...)` 필터 벡터 검색
12. LLM이 검색 결과를 바탕으로 최종 답변 생성, `_collect_sources()`로 출처 첨부

**Step 2: ReAct Agent 동작 원리 설명**

```
사용자 질문
    ↓
[Reason] "이 질문에 답하려면 NCS 문서를 검색해야 해"
    ↓
[Act] retrieve_context("SW 아키텍처 수행관리") 호출
    ↓
[Observe] 검색 결과 4개 문서 반환
    ↓
[Reason] "이 내용으로 답변 가능해"
    ↓
[Final Answer] 마크다운 형식 답변 생성
```

**Step 3: doc_id IN 필터가 왜 중요한지 설명**

카테고리 필터 없이 전체 검색 시 → 관련 없는 카테고리 문서가 섞임
doc_id IN 필터 → Oracle에서 "정보기술개발/SW아키텍쳐"에 해당하는 문서만 검색

```python
filter_dict = {"doc_id": {"$in": doc_ids}}
await self.vector_store.asimilarity_search(query, k=4, filter=filter_dict)
```

**Step 4: ToolBuilder 클로저 패턴 설명**

```python
def build_tools(self, doc_ids=None):
    _doc_ids = doc_ids or []   # 클로저로 캡처

    @tool
    async def retrieve_context(query: str):
        # _doc_ids가 외부 스코프에서 캡처됨
        return await vsm.similarity_search_by_doc_ids(query, doc_ids=_doc_ids)

    return [retrieve_context]
```

**Step 5: Commit**

```bash
git add docs/plans/2026-02-20-project-review.md
git commit -m "docs(review): 섹션 3 - RAG 채팅 시나리오"
```

---

## Task 4: 섹션 4 — 지원 시스템 작성

**Files:**
- Modify: `docs/plans/2026-02-20-project-review.md`

참고 파일:
- `ai_server/prompt_loader.py`
- `ai_server/agent.py` (`_build_system_prompt`, `_PROMPT_KEYS`)
- `backend/.../service/PromptService.java`
- `backend/.../controller/PromptController.java`
- `ai_server/tracing.py`
- `server.py:24-26`

**Step 1: Redis 프롬프트 관리 설명**

5개 프롬프트 키와 역할:
| 키 | 역할 |
|----|------|
| `agent_system_prompt` | AI 기본 역할 정의 |
| `answer_format_prompt` | 답변 형식 지침 (마크다운, 출처 표시) |
| `no_document_prompt` | 문서 없을 때 안내 메시지 |
| `query_enhance_prompt` | 검색 쿼리 최적화 지침 |
| `category_hint_prompt` | 카테고리 미선택 시 안내 |

`_build_system_prompt()` 동작:
```python
parts = [p for k in _PROMPT_KEYS if (p := get_prompt(k))]
return "\n\n".join(parts)
```

Spring `PromptController.set()` → Redis `prompt:<key>` 저장 → Python `get_prompt()` 로드 → fallback 처리.

**Step 2: Arize Phoenix 트레이싱 설명**

```
server.py 시작
    → setup_tracing() 최우선 호출
    → LangChainInstrumentor().instrument()
    → 이후 모든 LangChain 호출이 자동 계측됨
    → http://localhost:6006 대시보드에서 확인
```

**Step 3: 왜 tracing을 맨 먼저 초기화하는지 설명**

OpenTelemetry는 import 시점에 계측을 패치하므로 LangChain import 이전에 호출해야 한다. `server.py` 상단 2줄:
```python
from tracing import setup_tracing
setup_tracing()   # LangChain import 전
```

**Step 4: Commit**

```bash
git add docs/plans/2026-02-20-project-review.md
git commit -m "docs(review): 섹션 4 - Redis 프롬프트 + Arize Phoenix 지원 시스템"
```

---

## Task 5: 리뷰 문서 최종 점검

**Files:**
- Modify: `docs/plans/2026-02-20-project-review.md`

**Step 1: 전체 흐름 요약 다이어그램 추가**

```
[사용자]
   │ PDF 업로드                          │ 채팅 질문
   ▼                                     ▼
[Vue.js :5174]──────────────────────[Vue.js :5174]
   │ POST /api/documents                 │ POST /api/chat
   ▼                                     ▼
[Spring :8080]                      [Spring :8080]
   │ 1. Oracle INSERT (PENDING)          │ 1. Oracle → doc_ids 조회
   │ 2. POST /internal/ingest            │ 2. POST /internal/chat
   ▼                                     ▼
[Python :8000]                      [Python :8000]
   │ PDF→청크→임베딩                      │ ReAct Agent 실행
   │ PGVector 저장                        │   ↳ retrieve_context()
   │                                     │   ↳ PGVector 필터 검색
   ▼                                     │   ↳ LLM 응답 생성
Oracle status=INDEXED                    ▼
                                    답변 + 출처 반환
```

**Step 2: 핵심 설계 결정 요약 추가**

- **왜 Spring이 API Gateway인가:** 보안, 인증, 파일 저장 등 웹 서버 기능은 Java 생태계가 성숙. Python은 AI에만 집중.
- **왜 doc_id가 UUID인가:** 분산 환경에서 충돌 없는 고유 ID. DB auto-increment는 단일 DB에서만 유일.
- **왜 청크 overlap이 200인가:** 청크 경계에서 문맥이 잘리면 검색 품질 저하. 앞뒤 200자를 중복 저장해 경계 정보 보존.
- **왜 프롬프트를 Redis에 저장하는가:** 프롬프트 수정 시 서버 재배포 불필요. Spring Admin UI로 런타임 수정 가능.
- **왜 tracing을 최상단에 두는가:** OpenTelemetry 계측은 import 시점 패치이므로 LangChain보다 먼저 로드해야 함.

**Step 3: Commit**

```bash
git add docs/plans/2026-02-20-project-review.md
git commit -m "docs(review): 최종 점검 - 전체 흐름 요약 다이어그램 + 핵심 설계 결정 추가"
```
