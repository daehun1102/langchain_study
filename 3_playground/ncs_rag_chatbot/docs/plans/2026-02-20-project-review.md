# NCS RAG Chatbot — 프로젝트 리뷰

> 주니어 개발자가 NCS RAG Chatbot의 전체 기능 흐름을 코드 레벨로 단계적으로 이해할 수 있도록 작성된 리뷰 문서입니다.

**Tech Stack:** Spring Boot 4.0.2 / MyBatis / RestClient · Python FastAPI / LangGraph / langchain-postgres · Oracle DB / PostgreSQL+pgvector / Redis · Arize Phoenix · Vue.js 3 / Vite

---

## 섹션 1: 전체 아키텍처 개요

### 1-1. 서버 3개를 왜 분리했는가

이 프로젝트는 세 개의 독립된 서버로 구성됩니다.

**Spring Boot (포트 8080) — 외부 공개 API Gateway**

파일 업로드, 인증, DB CRUD 등 전통적인 "웹 서버" 역할을 담당합니다. 보안 필터, 인증/인가, 파일 저장 등은 Java/Spring 생태계가 수십 년간 다져온 영역입니다. 외부 클라이언트(Vue.js)가 바라보는 유일한 서버입니다.

**Python FastAPI (포트 8000) — 순수 AI 추론 서버**

LangChain, LangGraph, HuggingFace 등 AI 라이브러리는 Python 생태계가 압도적으로 풍부합니다. 이 서버는 외부에 노출되지 않고 Spring만 내부적으로 호출합니다. AI 기능에만 집중할 수 있도록 역할을 분리했습니다.

**Vue.js (포트 5174) — 프론트엔드 SPA**

브라우저에서 동작하는 Single Page Application입니다. Spring Boot만 바라보며 Python 서버를 직접 호출하지 않습니다. 이렇게 하면 AI 서버 변경이 프론트엔드에 영향을 주지 않습니다.

```
브라우저
  │
  ▼
Vue.js :5174
  │  (HTTP)
  ▼
Spring Boot :8080  ──────────────────┐
  │  (내부 HTTP)                     │
  ▼                                  ▼
Python FastAPI :8000              Oracle :1521
  │
  ▼
PGVector :5432
```

---

### 1-2. 데이터베이스를 왜 3개로 분리했는가

| DB | 용도 | 선택 이유 |
|----|------|----------|
| Oracle | 문서 메타데이터 (파일명, 카테고리, 상태) | 관계형 데이터에 적합. 기업 환경 표준 RDBMS. |
| PostgreSQL + pgvector | 벡터 임베딩 저장 | PostgreSQL 확장으로 SQL과 벡터 검색을 동시에. 별도 벡터 DB 없이 사용 가능. |
| Redis | 시스템 프롬프트 저장 | 재배포 없이 런타임에 수정 가능. 키-값 구조로 단순하고 빠름. |

각 DB는 다른 목적을 위해 최적화되어 있습니다. 하나의 DB에 모두 넣을 수도 있지만, 벡터 검색과 관계형 쿼리를 같은 DB에서 처리하면 성능과 유지보수 모두 어려워집니다.

---

### 1-3. doc_id 연결 구조

두 DB는 `doc_id` (UUID)로 연결됩니다.

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

`doc_id`는 UUID이며, 두 DB를 연결하는 유일한 키입니다. PGVector는 Oracle을 참조하되 FK 제약은 없고, 애플리케이션 레벨에서 일관성을 유지합니다.

**왜 UUID인가?** DB auto-increment는 단일 DB에서만 유일합니다. 분산 환경에서 충돌 없는 고유 ID를 보장하려면 UUID가 필요합니다.

---

### 1-4. 전체 포트 맵

| 서버 | 포트 | 누가 호출하나 |
|------|------|-------------|
| Vue.js | 5174 | 브라우저 |
| Spring Boot | 8080 | Vue.js |
| Python FastAPI | 8000 | Spring만 |
| Oracle | 1521 | Spring만 |
| PGVector | 5432 | Python만 |
| Redis | 6379 | Spring + Python |
| Arize Phoenix | 6006/4317 | Python만 |

---

## 섹션 2: 시나리오 1 — PDF 업로드 흐름 (11단계)

PDF 한 장을 업로드하면 어떤 일이 일어나는지 코드 레벨로 추적합니다.

---

### Step 1: 사용자가 파일을 선택하고 카테고리를 지정 (`DocumentView.vue`)

**무엇을 하는가:** 사용자가 파일 선택 + 대분류/소분류 카테고리를 입력한 뒤 업로드 버튼을 클릭합니다.

**핵심 코드:**
```vue
<!-- DocumentView.vue -->
<input type="file" @change="onFileChange" accept=".pdf" />
<select v-model="mainCategory">...</select>
<button @click="uploadDocument">업로드</button>
```

**왜 이렇게 했는가:** 카테고리는 나중에 RAG 채팅에서 검색 범위를 필터링하는 핵심 키입니다. 업로드 시점에 반드시 받아야 합니다.

---

### Step 2: `ncsApi.js:uploadDocument()` — FormData 빌드 + `POST /api/documents`

**무엇을 하는가:** 파일과 카테고리 정보를 FormData로 묶어 Spring에 전송합니다.

**핵심 코드:**
```javascript
// ncsApi.js
export const uploadDocument = (file, mainCategory, subCategory) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('mainCategory', mainCategory)
  formData.append('subCategory', subCategory)
  return apiClient.post('/api/documents', formData)
}
```

**왜 이렇게 했는가:** 바이너리 파일(PDF)과 텍스트 필드를 함께 전송하려면 `multipart/form-data`가 표준입니다. JSON으로는 바이너리를 직접 담기 어렵습니다.

---

### Step 3: `DocumentController.upload()` — `@RequestParam MultipartFile` 수신

**무엇을 하는가:** Spring Controller가 멀티파트 요청을 받아 Service로 넘깁니다.

**핵심 코드:**
```java
// DocumentController.java
@PostMapping("/api/documents")
public ResponseEntity<?> upload(
    @RequestParam MultipartFile file,
    @RequestParam String mainCategory,
    @RequestParam String subCategory) {
    return documentService.upload(file, mainCategory, subCategory);
}
```

**왜 이렇게 했는가:** `@RequestParam`으로 멀티파트 필드를 각각 바인딩합니다. Controller는 요청 수신과 응답 반환만 담당하고, 비즈니스 로직은 Service에 위임합니다.

---

### Step 4: `DocumentService.upload()` — UUID 발급 + 파일 저장 + Oracle INSERT (PENDING)

**무엇을 하는가:** UUID를 생성하고, 파일을 디스크에 저장하고, Oracle에 상태 `PENDING`으로 메타데이터를 INSERT합니다.

**핵심 코드:**
```java
// DocumentService.java
String docId = UUID.randomUUID().toString();
Path savedPath = fileStorage.save(file, docId);
documentMapper.insert(new Document(docId, filename, mainCategory, subCategory, "PENDING"));
```

**왜 이렇게 했는가:** 먼저 `PENDING` 상태로 저장해두면 Python 처리 도중 서버가 죽어도 미완료 문서를 추적할 수 있습니다. UUID는 분산 환경에서 충돌 없는 고유 ID를 보장합니다.

---

### Step 5: `DocumentMapper.insert()` — MyBatis XML `<insert>` 실행

**무엇을 하는가:** MyBatis XML Mapper가 Oracle에 INSERT SQL을 실행합니다.

**핵심 코드:**
```xml
<!-- DocumentMapper.xml -->
<insert id="insert" parameterType="Document">
    INSERT INTO documents (doc_id, filename, main_category, sub_category, status)
    VALUES (#{docId}, #{filename}, #{mainCategory}, #{subCategory}, #{status})
</insert>
```

**왜 이렇게 했는가:** MyBatis는 SQL을 XML에 명시적으로 작성합니다. JPA처럼 SQL을 숨기지 않아 복잡한 쿼리 튜닝이 필요한 프로젝트에 적합합니다.

---

### Step 6: `DocumentService`가 `RestClient.post("/internal/ingest")` 호출

**무엇을 하는가:** Spring이 Python AI 서버로 내부 HTTP 요청을 보내 임베딩 처리를 요청합니다.

**핵심 코드:**
```java
// DocumentService.java
restClient.post()
    .uri("/internal/ingest")
    .body(new IngestRequest(docId, savedPath.toString()))
    .retrieve()
    .toBodilessEntity();
```

**왜 이렇게 했는가:** Spring과 Python은 서로 다른 프로세스이므로 HTTP로 통신합니다. `/internal/` prefix로 외부 노출이 아닌 내부 통신임을 명확히 표시합니다.

---

### Step 7: `server.py:ingest()` — `IngestRequest(doc_id, file_path)` 수신

**무엇을 하는가:** Python FastAPI 엔드포인트가 요청을 받아 파이프라인을 시작합니다.

**핵심 코드:**
```python
# server.py
@app.post("/internal/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    chunks = await ingest_single_document(req.doc_id, req.file_path, DB_CONNECTION)
    return IngestResponse(doc_id=req.doc_id, chunks=chunks, status="INDEXED")
```

**왜 이렇게 했는가:** Python 서버는 AI 처리에만 집중합니다. `doc_id`, `file_path`, DB 연결 문자열을 받아 처리하고, 저장된 청크 수와 상태를 Spring에 돌려줍니다. Spring은 이 응답의 `status` 필드를 보고 Oracle을 `INDEXED`로 업데이트합니다.

---

### Step 8: `ingest.py:ingest_single_document()` — 전체 파이프라인 진입점

**무엇을 하는가:** PDF → 청크 → 임베딩 → 저장의 전체 파이프라인을 순서대로 실행합니다.

**핵심 코드:**
```python
# ingest.py
async def ingest_single_document(doc_id: str, file_path: str):
    docs = DocumentLoader(file_path).load()
    splits = DocumentSplitter().split_documents(docs)
    await EmbeddingModel().get_embeddings(doc_id, splits)
```

**왜 이렇게 했는가:** 각 단계를 별도 클래스로 분리해 단일 책임 원칙을 따릅니다. 단계별로 교체나 테스트가 용이합니다.

---

### Step 9: `DocumentLoader.load()` → `DocumentSplitter.split_documents()` — PDF를 청크로 분할

**무엇을 하는가:** PDF 파일을 텍스트로 변환하고, 검색에 적합한 크기의 청크로 분할합니다.

**핵심 코드:**
```python
# splitter.py
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
splits = splitter.split_documents(docs)
```

**왜 이렇게 했는가:**

```
[     1000자     ]
          [     1000자     ]
     ←200→ (overlap: 문맥 연속성 보장)
```

청크 경계에서 문맥이 잘리면 검색 품질이 저하됩니다. 앞뒤 200자를 중복 저장해 경계 정보를 보존합니다.

---

### Step 10: `EmbeddingModel.get_embeddings()` + `PGVectorStore.aadd_documents()` — 임베딩 후 저장

**무엇을 하는가:** 각 청크를 벡터로 변환하고, `doc_id`와 페이지 정보를 메타데이터로 붙여 PGVector에 저장합니다.

**핵심 코드:**
```python
# embeddings.py / vector_store.py
for doc in splits:
    doc.metadata["doc_id"] = doc_id   # Oracle과 연결
    doc.metadata["page"] = doc.metadata.get("page", 0)
await self.vector_store.aadd_documents(splits)
```

**왜 이렇게 했는가:** `doc_id`를 메타데이터에 붙여야 나중에 "이 문서들만 검색"하는 필터 쿼리가 가능합니다. Oracle과의 연결 고리가 됩니다.

---

### Step 11: Spring이 응답을 받아 `DocumentMapper.updateStatus(INDEXED)` 호출

**무엇을 하는가:** Python 처리가 성공하면 Spring이 Oracle의 문서 상태를 `INDEXED`로 업데이트합니다.

**핵심 코드:**
```java
// DocumentService.java
try {
    restClient.post().uri("/internal/ingest")...retrieve();
    documentMapper.updateStatus(docId, "INDEXED");
} catch (Exception e) {
    documentMapper.updateStatus(docId, "FAILED");
}
```

**왜 이렇게 했는가:** 상태 전이를 명확히 관리합니다:

```
업로드 시작 → PENDING (Oracle INSERT)
               ↓
         Python ingest 성공 → INDEXED
         Python ingest 실패 → FAILED
```

`INDEXED` 상태인 문서만 RAG 채팅에서 검색 대상이 됩니다.

---

## 섹션 3: 시나리오 2 — RAG 채팅 흐름 (12단계)

사용자가 질문을 입력하면 어떻게 관련 문서를 찾아 답변하는지 추적합니다.

---

### Step 1: 사용자가 채팅 입력창에 질문 + 카테고리 선택 (`ChatInput.vue`)

**무엇을 하는가:** 사용자가 자연어 질문을 입력하고, 검색할 카테고리를 선택합니다.

**핵심 코드:**
```vue
<!-- ChatInput.vue -->
<textarea v-model="query" placeholder="질문을 입력하세요" />
<select v-model="mainCategory">...</select>
<button @click="sendChat">전송</button>
```

**왜 이렇게 했는가:** 카테고리를 지정하면 검색 범위를 좁혀 관련성 높은 결과를 얻을 수 있습니다. 지정하지 않으면 전체 문서에서 검색합니다.

---

### Step 2: `ncsApi.js:sendChat(query, mainCategory, subCategory)` — `POST /api/chat`

**무엇을 하는가:** 질문과 카테고리 정보를 JSON으로 Spring에 전송합니다.

**핵심 코드:**
```javascript
// ncsApi.js
export const sendChat = (query, mainCategory, subCategory) => {
  return apiClient.post('/api/chat', { query, mainCategory, subCategory })
}
```

**왜 이렇게 했는가:** 채팅은 텍스트 데이터만 전송하므로 JSON이 적합합니다.

---

### Step 3: `ChatController.chat()` — `@RequestBody ChatRequest` 수신

**무엇을 하는가:** Spring Controller가 채팅 요청을 받아 Service로 넘깁니다.

**핵심 코드:**
```java
// ChatController.java
@PostMapping("/api/chat")
public ResponseEntity<?> chat(@RequestBody ChatRequest request) {
    return chatService.chat(request);
}
```

**왜 이렇게 했는가:** `@RequestBody`로 JSON을 Java 객체로 자동 변환합니다.

---

### Step 4: `ChatService.chat()` — 카테고리 조건으로 Oracle 조회 시작

**무엇을 하는가:** 카테고리 조건에 맞는 `INDEXED` 상태 문서의 `doc_id` 목록을 조회합니다.

**핵심 코드:**
```java
// ChatService.java
List<String> docIds = documentMapper.findDocIdsByCategory(
    request.getMainCategory(), request.getSubCategory()
);
```

**왜 이렇게 했는가:** 벡터 검색 전에 Oracle에서 검색 범위를 좁힙니다. "이 카테고리의 INDEXED 문서들"만 벡터 검색 대상으로 설정합니다.

---

### Step 5: `DocumentMapper.findDocIdsByCategory()` — `WHERE status='INDEXED' AND main_category=?` → doc_id 목록 반환

**무엇을 하는가:** Oracle에서 카테고리와 상태 조건으로 `doc_id` 목록을 가져옵니다.

**핵심 코드:**
```xml
<!-- DocumentMapper.xml -->
<select id="findDocIdsByCategory" resultType="String">
    SELECT doc_id FROM documents
    WHERE status = 'INDEXED'
    <if test="mainCategory != null">AND main_category = #{mainCategory}</if>
    <if test="subCategory != null">AND sub_category = #{subCategory}</if>
</select>
```

**왜 이렇게 했는가:** MyBatis의 동적 SQL(`<if>`)로 카테고리 미선택 시 전체 검색, 선택 시 필터 검색을 하나의 쿼리로 처리합니다.

---

### Step 6: `RestClient.post("/internal/chat")` — `{query, doc_ids}` Python 전달

**무엇을 하는가:** Spring이 `doc_ids` 목록과 질문을 Python 서버로 전달합니다.

**핵심 코드:**
```java
// ChatService.java
ChatResponse response = restClient.post()
    .uri("/internal/chat")
    .body(new PythonChatRequest(request.getQuery(), docIds))
    .retrieve()
    .body(ChatResponse.class);
```

**왜 이렇게 했는가:** Python은 벡터 검색을 직접 하지 않고 "이 doc_id들 안에서만 검색하라"는 지시를 받습니다. 검색 범위 결정 권한은 Spring(Oracle)이 갖습니다.

---

### Step 7: `server.py:chat()` — `ChatRequest(query, doc_ids)` 수신

**무엇을 하는가:** Python FastAPI가 채팅 요청을 받아 Agent를 준비합니다.

**핵심 코드:**
```python
# server.py
@app.post("/internal/chat")
async def chat(request: ChatRequest):
    tools = tool_builder.build_tools(doc_ids=request.doc_ids)
    agent = chat_agent.create_agent(tools)
    result = await agent.run(request.query)
    return result
```

**왜 이렇게 했는가:** 매 요청마다 `doc_ids`를 캡처한 새 도구를 만들고 Agent를 구성합니다. 요청별로 검색 범위가 독립적으로 격리됩니다.

---

### Step 8: `ToolBuilder.build_tools(doc_ids)` — doc_ids를 클로저로 캡처한 검색 도구 생성

**무엇을 하는가:** `doc_ids`를 클로저로 캡처하는 `retrieve_context` 도구 함수를 동적으로 생성합니다.

**핵심 코드:**
```python
# tool.py
def build_tools(self, doc_ids=None):
    _doc_ids = doc_ids or []   # 클로저로 캡처

    @tool
    async def retrieve_context(query: str):
        # _doc_ids가 외부 스코프에서 캡처됨
        return await vsm.similarity_search_by_doc_ids(query, doc_ids=_doc_ids)

    return [retrieve_context]
```

**왜 이렇게 했는가:** LangChain `@tool` 데코레이터는 `query: str` 하나만 받습니다. `doc_ids`를 클로저로 숨겨두면 LLM이 `doc_ids`를 알 필요 없이 자연어 쿼리만으로 검색 도구를 호출할 수 있습니다.

---

### Step 9: `ChatAgent.create_agent(tools)` — LangGraph `create_react_agent()` 호출

**무엇을 하는가:** 도구 목록을 받아 ReAct Agent를 생성합니다.

**핵심 코드:**
```python
# agent.py
def create_agent(self, tools):
    system_prompt = self._build_system_prompt()
    return create_react_agent(
        model=self.llm,
        tools=tools,
        prompt=system_prompt
    )
```

**왜 이렇게 했는가:** LangGraph의 `create_react_agent`는 Reason-Act-Observe 루프를 자동으로 처리합니다. 도구 호출 여부, 반복 여부를 LLM이 스스로 결정합니다.

---

### Step 10: `agent.run(query)` — ReAct 루프 시작

**무엇을 하는가:** Agent가 질문을 분석하고 필요하면 도구를 호출하는 루프를 실행합니다.

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

**왜 이렇게 했는가:** 단순 프롬프트 방식은 항상 검색을 합니다. ReAct는 "검색이 필요한가?"를 LLM이 스스로 판단합니다. 불필요한 검색을 줄이고 맥락에 맞는 답변을 생성합니다.

---

### Step 11: `retrieve_context(query)` → `similarity_search_by_doc_ids()` — `doc_id IN (...)` 필터 벡터 검색

**무엇을 하는가:** PGVector에서 `doc_ids` 범위 안에서만 유사도 검색을 수행합니다.

**핵심 코드:**
```python
# vector_store.py
async def similarity_search_by_doc_ids(self, query: str, doc_ids: list, k: int = 4):
    filter_dict = {"doc_id": {"$in": doc_ids}}
    return await self.vector_store.asimilarity_search(
        query, k=k, filter=filter_dict
    )
```

**왜 이렇게 했는가:** 카테고리 필터 없이 전체 검색하면 관련 없는 카테고리 문서가 섞입니다. `doc_id IN (...)` 필터로 Oracle에서 결정한 범위 안에서만 검색합니다.

---

### Step 12: LLM이 검색 결과를 바탕으로 최종 답변 생성, `_collect_sources()`로 출처 첨부

**무엇을 하는가:** LLM이 검색된 청크들을 참고해 답변을 생성하고, 어떤 문서에서 왔는지 출처를 첨부합니다.

**핵심 코드:**
```python
# agent.py
def _collect_sources(self, result) -> list:
    sources = []
    for msg in result.get("messages", []):
        if hasattr(msg, "artifact"):
            sources.extend(msg.artifact)
    return sources
```

**왜 이렇게 했는가:** RAG의 핵심은 "어디서 왔는지"를 투명하게 보여주는 것입니다. 출처를 첨부하면 사용자가 답변의 근거를 직접 확인할 수 있습니다.

---

## 섹션 4: 지원 시스템

### 4-1. Redis 프롬프트 관리

시스템 프롬프트를 Redis에 저장하면 서버 재배포 없이 런타임에 수정할 수 있습니다.

**5개 프롬프트 키와 역할:**

| 키 | 역할 |
|----|------|
| `agent_system_prompt` | AI 기본 역할 정의 |
| `answer_format_prompt` | 답변 형식 지침 (마크다운, 출처 표시) |
| `no_document_prompt` | 문서 없을 때 안내 메시지 |
| `query_enhance_prompt` | 검색 쿼리 최적화 지침 |
| `category_hint_prompt` | 카테고리 미선택 시 안내 |

**`_build_system_prompt()` 동작:**
```python
# agent.py
def _build_system_prompt(self) -> str:
    parts = [p for k in _PROMPT_KEYS if (p := get_prompt(k))]
    return "\n\n".join(parts)
```

5개 키를 순서대로 조회해 존재하는 것만 조합합니다. 일부 키가 Redis에 없어도 나머지로 정상 동작합니다.

**전체 흐름:**
```
Spring PromptController.set()
    → Redis "prompt:<key>" 저장
    → Python get_prompt(key) 로드
    → Redis 없으면 기본값 fallback
    → _build_system_prompt()로 조합
    → Agent system prompt로 주입
```

**왜 Redis에 저장하는가?** 프롬프트 수정 시 서버 재배포가 불필요합니다. Spring Admin UI에서 런타임에 수정하면 다음 요청부터 즉시 반영됩니다.

---

### 4-2. Arize Phoenix 트레이싱

LLM 호출의 내부 동작을 시각적으로 모니터링합니다.

**초기화 흐름:**
```
server.py 시작
    → setup_tracing() 최우선 호출
    → LangChainInstrumentor().instrument()
    → 이후 모든 LangChain 호출이 자동 계측됨
    → http://localhost:6006 대시보드에서 확인
```

**핵심 코드:**
```python
# server.py (최상단)
from tracing import setup_tracing
setup_tracing()   # LangChain import 전에 호출

# 이후에 LangChain 관련 import...
from agent import ChatAgent
```

**왜 tracing을 맨 먼저 초기화하는가?**

OpenTelemetry는 import 시점에 라이브러리를 패치(monkey-patch)합니다. `LangChainInstrumentor().instrument()`는 LangChain의 체인, 모델, 도구 호출 클래스에 계측 코드를 삽입합니다. **LangChain이 import된 이후에 호출하면 이미 로드된 클래스는 패치되지 않습니다.** 따라서 반드시 모든 LangChain import보다 먼저 호출해야 합니다.

**Arize Phoenix에서 확인할 수 있는 것:**
- ReAct Agent의 Reason-Act-Observe 각 단계 소요 시간
- 도구 호출 입력/출력
- LLM 프롬프트 전체 내용 및 토큰 사용량
- 검색 결과 청크 내용

---
