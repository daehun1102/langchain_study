# NCS RAG Chatbot — 프롬프트 관리 / 탭 UI / 삭제 일관성 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redis 초기 프롬프트 5개 관리, 프론트엔드 대화/문서관리 탭 분리, 문서 삭제 시 Oracle+PGVector+파일 동시 정리를 구현한다.

**Architecture:** Spring Boot(8080)가 API Gateway, Python FastAPI(8000)가 AI 추론 담당. 삭제 흐름은 Spring → Python `/internal/delete/{docId}` → PGVector 청크 삭제 → Oracle 삭제 순. 프롬프트는 Redis에 5개 key로 분리 저장하며 agent.py에서 결합하여 사용.

**Tech Stack:** Python FastAPI / LangChain / langchain-postgres / Redis / Spring Boot 4 / RestClient / Vue 3 / Vite

---

## 의존 관계

```
Task 1 → Task 2 → Task 3          (프롬프트, 순차)
Task 4 → Task 5 → Task 6          (삭제, 순차)
Task 7 → Task 8 → Task 9          (프론트, 순차)

Task 1-3, Task 4-6, Task 7-9 세 그룹은 서로 독립적으로 병렬 진행 가능
```

---

## Task 1: init_prompts.py — 5개 프롬프트 Redis 등록

**Files:**
- Modify: `src/init_prompts.py`

**Step 1: init_prompts.py 전체 교체**

```python
"""
init_prompts.py — Redis에 초기 프롬프트 데이터를 등록하는 스크립트

실행: python src/init_prompts.py
Redis가 실행 중이어야 합니다.
"""

import redis
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
PREFIX = "prompt:"

PROMPTS = {
    "agent_system_prompt": (
        "너는 NCS(국가직무능력표준) 문서에서 정보를 검색하여 답변해주는 친절한 AI 어시스턴트야.\n"
        "사용자의 질의에 항상 retrieve_context 도구를 사용해서 먼저 관련 문서를 검색하고 답변해줘.\n"
        "문서에서 찾은 내용만 답변하고, 모르는 내용은 추측하지 마."
    ),
    "answer_format_prompt": (
        "답변 형식 지침:\n"
        "- 마크다운 형식으로 작성해줘 (헤딩, 목록, 굵게 등 적극 활용)\n"
        "- 답변 말미에 출처를 명시해줘: '출처: 페이지 {페이지번호}'\n"
        "- 여러 문서에서 정보를 가져왔다면 각 내용의 출처를 구분해서 표시해줘\n"
        "- 불확실한 내용은 반드시 '문서에서 확인되지 않음'이라고 표시해줘"
    ),
    "no_document_prompt": (
        "관련 문서를 찾지 못했을 때 안내:\n"
        "retrieve_context 도구로 검색했으나 관련 내용을 찾지 못한 경우, 다음과 같이 안내해줘:\n"
        "'해당 카테고리에 등록된 문서에서 관련 내용을 찾을 수 없습니다. "
        "다른 카테고리를 선택하거나, 질문을 좀 더 구체적으로 바꿔보세요.'"
    ),
    "query_enhance_prompt": (
        "검색 쿼리 최적화 지침:\n"
        "- 사용자 질의가 짧거나 모호하면 NCS 문서 맥락에 맞게 구체화하여 검색해줘\n"
        "- 예: '테스트란?' → 'NCS IT테스트 기획 및 설계 방법'\n"
        "- 첫 검색 결과가 불충분하면 다른 키워드로 재검색해줘 (최대 2회)\n"
        "- 검색어는 한국어로 작성해줘"
    ),
    "category_hint_prompt": (
        "카테고리 안내:\n"
        "카테고리가 선택되지 않아 전체 문서에서 검색합니다.\n"
        "답변 말미에 다음 문구를 추가해줘:\n"
        "'💡 좌측 카테고리 필터를 선택하면 특정 분야의 문서만 검색하여 더 정확한 답변을 받을 수 있습니다.'"
    ),
}

if __name__ == "__main__":
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    try:
        r.ping()
    except redis.ConnectionError:
        print(f"[ERROR] Redis에 연결할 수 없습니다: {REDIS_HOST}:{REDIS_PORT}")
        raise SystemExit(1)

    for key, value in PROMPTS.items():
        r.set(PREFIX + key, value)
        print(f"[init_prompts] 저장 완료: {PREFIX + key}")

    print(f"\n총 {len(PROMPTS)}개 프롬프트 등록 완료")
    print("확인: redis-cli keys 'prompt:*'")
```

**Step 2: 실행 및 검증**

```bash
# 프로젝트 루트에서
source venv/Scripts/activate
python src/init_prompts.py
```

Expected:
```
[init_prompts] 저장 완료: prompt:agent_system_prompt
[init_prompts] 저장 완료: prompt:answer_format_prompt
[init_prompts] 저장 완료: prompt:no_document_prompt
[init_prompts] 저장 완료: prompt:query_enhance_prompt
[init_prompts] 저장 완료: prompt:category_hint_prompt

총 5개 프롬프트 등록 완료
```

Redis에서 직접 확인:
```bash
redis-cli keys "prompt:*"
# 결과: 5개 키 출력
redis-cli get "prompt:answer_format_prompt"
# 결과: 프롬프트 텍스트 출력
```

**Step 3: Commit**

```bash
git add src/init_prompts.py
git commit -m "feat(python): Redis 초기 프롬프트 5개 등록 (init_prompts.py)"
```

---

## Task 2: prompt_loader.py — fallback 5개 추가

**Files:**
- Modify: `src/prompt_loader.py`

**Step 1: FALLBACK_PROMPTS를 5개로 확장**

`src/prompt_loader.py`에서 `FALLBACK_PROMPTS` 딕셔너리를 교체:

```python
# Redis 연결 실패 시 사용하는 기본 프롬프트
FALLBACK_PROMPTS = {
    "agent_system_prompt": (
        "너는 NCS(국가직무능력표준) 문서에서 정보를 검색하여 답변해주는 친절한 AI 어시스턴트야.\n"
        "사용자의 질의에 항상 retrieve_context 도구를 사용해서 먼저 관련 문서를 검색하고 답변해줘.\n"
        "문서에서 찾은 내용만 답변하고, 모르는 내용은 추측하지 마."
    ),
    "answer_format_prompt": (
        "답변 형식 지침:\n"
        "- 마크다운 형식으로 작성해줘 (헤딩, 목록, 굵게 등 적극 활용)\n"
        "- 답변 말미에 출처를 명시해줘: '출처: 페이지 {페이지번호}'\n"
        "- 여러 문서에서 정보를 가져왔다면 각 내용의 출처를 구분해서 표시해줘\n"
        "- 불확실한 내용은 반드시 '문서에서 확인되지 않음'이라고 표시해줘"
    ),
    "no_document_prompt": (
        "관련 문서를 찾지 못했을 때 안내:\n"
        "retrieve_context 도구로 검색했으나 관련 내용을 찾지 못한 경우, 다음과 같이 안내해줘:\n"
        "'해당 카테고리에 등록된 문서에서 관련 내용을 찾을 수 없습니다. "
        "다른 카테고리를 선택하거나, 질문을 좀 더 구체적으로 바꿔보세요.'"
    ),
    "query_enhance_prompt": (
        "검색 쿼리 최적화 지침:\n"
        "- 사용자 질의가 짧거나 모호하면 NCS 문서 맥락에 맞게 구체화하여 검색해줘\n"
        "- 예: '테스트란?' → 'NCS IT테스트 기획 및 설계 방법'\n"
        "- 첫 검색 결과가 불충분하면 다른 키워드로 재검색해줘 (최대 2회)\n"
        "- 검색어는 한국어로 작성해줘"
    ),
    "category_hint_prompt": (
        "카테고리 안내:\n"
        "카테고리가 선택되지 않아 전체 문서에서 검색합니다.\n"
        "답변 말미에 다음 문구를 추가해줘:\n"
        "'💡 좌측 카테고리 필터를 선택하면 특정 분야의 문서만 검색하여 더 정확한 답변을 받을 수 있습니다.'"
    ),
}
```

**Step 2: 검증**

```bash
source venv/Scripts/activate
python -c "
import sys; sys.path.insert(0, 'src')
# Redis 없이 fallback 테스트
from unittest.mock import patch
import redis
with patch.object(redis.Redis, 'get', side_effect=redis.ConnectionError('test')):
    from prompt_loader import get_prompt
    result = get_prompt('answer_format_prompt')
    assert '마크다운' in result, f'fallback 실패: {result}'
    print('fallback 테스트 통과:', result[:50])
"
```

**Step 3: Commit**

```bash
git add src/prompt_loader.py
git commit -m "feat(python): prompt_loader fallback 5개 추가"
```

---

## Task 3: agent.py — _build_system_prompt() 추가

**Files:**
- Modify: `src/agent.py`

**Step 1: agent.py 수정**

현재 `agent.py` 전체를 아래로 교체:

```python
"""
agent.py — LangChain/LangGraph 기반 채팅 에이전트

Phase 3 변경:
- 하드코딩 시스템 프롬프트 제거
- Redis에서 프롬프트 로드 (prompt_loader.get_prompt)
- Redis 연결 실패 시 fallback 프롬프트 사용

Phase 3.1 변경:
- _build_system_prompt(): 5개 프롬프트를 결합하여 단일 system_prompt 생성
"""

from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from prompt_loader import get_prompt
from typing import List


_PROMPT_KEYS = [
    "agent_system_prompt",
    "answer_format_prompt",
    "no_document_prompt",
    "query_enhance_prompt",
    "category_hint_prompt",
]


def _build_system_prompt() -> str:
    """Redis에서 5개 프롬프트를 로드하여 하나의 system prompt로 결합한다.

    Redis에서 키를 찾지 못하면 fallback 값을 사용한다.
    빈 문자열인 프롬프트는 결합에서 제외한다.
    """
    parts = [p for k in _PROMPT_KEYS if (p := get_prompt(k))]
    return "\n\n".join(parts)


class ChatAgent:

    def __init__(self, model_name: str = "gpt-4o-mini", system_prompt: str = None):
        self.model = init_chat_model(model_name)
        # system_prompt가 명시적으로 전달되면 사용, 없으면 Redis 5개 통합 로드
        if system_prompt is not None:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = _build_system_prompt()

    def create_agent(self, tools: List):
        """모델과 도구를 결합하여 ReAct 에이전트를 생성한다."""
        self.agent = create_react_agent(
            self.model,
            tools,
            prompt=self.system_prompt,
        )

    async def run(self, query: str):
        """사용자 질의를 처리하고 마지막 메시지를 반환한다."""
        if not hasattr(self, "agent"):
            raise ValueError("Agent가 생성되지 않았습니다. create_agent()를 먼저 호출하세요.")

        last_message = None
        async for event in self.agent.astream(
            {"messages": [{"role": "user", "content": query}]},
            stream_mode="values",
        ):
            last_message = event["messages"][-1]

        return last_message
```

**Step 2: 프롬프트 로드 검증**

```bash
source venv/Scripts/activate
python -c "
import sys; sys.path.insert(0, 'src')
from agent import _build_system_prompt
prompt = _build_system_prompt()
print('=== 결합된 system prompt ===')
print(prompt)
print(f'\n총 길이: {len(prompt)} 글자')
assert '검색' in prompt, 'agent_system_prompt 없음'
assert '마크다운' in prompt, 'answer_format_prompt 없음'
assert '카테고리' in prompt, 'no_document_prompt 없음'
print('검증 통과')
"
```

Expected: 5개 프롬프트가 `\n\n`으로 연결된 전체 텍스트 출력

**Step 3: Commit**

```bash
git add src/agent.py
git commit -m "feat(python): agent.py에 _build_system_prompt() 추가 (5개 Redis 프롬프트 통합)"
```

---

## Task 4: vector_store.py — delete_by_doc_id() 추가

**Files:**
- Modify: `src/vector_store.py`

**Step 1: delete_by_doc_id 메서드 추가**

`src/vector_store.py`의 `get_vector_store()` 메서드 아래에 추가:

```python
    async def delete_by_doc_id(self, doc_id: str) -> int:
        """doc_id에 해당하는 모든 벡터 청크를 삭제한다.

        langchain-postgres는 메타데이터 필터로 벡터 삭제 API를 제공하지 않으므로
        SQLAlchemy를 통해 직접 SQL DELETE를 실행한다.

        Args:
            doc_id: Oracle documents 테이블의 doc_id (UUID)

        Returns:
            삭제된 청크(행) 수
        """
        from sqlalchemy import text
        # PGEngine 내부의 async SQLAlchemy engine에 직접 접근
        engine = self.pg_engine._engine
        async with engine.begin() as conn:
            result = await conn.execute(
                text(f"DELETE FROM {TABLE_NAME} WHERE doc_id = :doc_id"),
                {"doc_id": doc_id},
            )
            return result.rowcount
```

전체 파일은 아래와 같다:

```python
"""
vector_store.py — PGVectorStore 관리 모듈

변경 사항 (Phase 2):
- metadata_columns: doc_id + page만 사용
- similarity_search_by_doc_ids(): doc_id 목록으로 필터링 검색

변경 사항 (Phase 2.1):
- delete_by_doc_id(): doc_id 청크 일괄 삭제 (삭제 일관성)
"""

from langchain_postgres import PGEngine, PGVectorStore
from typing import List, Optional
from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import create_async_engine

TABLE_NAME = "ncs_vectors"


class VectorStoreManager:

    def __init__(self, pg_engine, vector_store):
        self.pg_engine = pg_engine
        self.vector_store = vector_store

    @classmethod
    async def create(cls, connection_string: str, embedding_model):
        """VectorStoreManager 인스턴스를 비동기로 생성한다."""
        engine = create_async_engine(connection_string)
        pg_engine = PGEngine.from_engine(engine)
        vector_store = await PGVectorStore.create(
            engine=pg_engine,
            table_name=TABLE_NAME,
            embedding_service=embedding_model,
            metadata_columns=["doc_id", "page"],
        )
        return cls(pg_engine, vector_store)

    async def similarity_search_by_doc_ids(
        self,
        query: str,
        doc_ids: Optional[List[str]] = None,
        k: int = 4,
    ) -> List[Document]:
        """doc_id 목록 범위 내에서 유사도 검색을 수행한다.

        doc_ids가 비어있으면 전체 벡터에서 검색한다.
        """
        if doc_ids:
            filter_dict = {"doc_id": {"$in": doc_ids}}
            return await self.vector_store.asimilarity_search(query, k=k, filter=filter_dict)
        return await self.vector_store.asimilarity_search(query, k=k)

    async def delete_by_doc_id(self, doc_id: str) -> int:
        """doc_id에 해당하는 모든 벡터 청크를 삭제한다.

        langchain-postgres는 메타데이터 필터로 벡터 삭제 API를 제공하지 않으므로
        SQLAlchemy를 통해 직접 SQL DELETE를 실행한다.

        Args:
            doc_id: Oracle documents 테이블의 doc_id (UUID)

        Returns:
            삭제된 청크(행) 수
        """
        from sqlalchemy import text
        engine = self.pg_engine._engine
        async with engine.begin() as conn:
            result = await conn.execute(
                text(f"DELETE FROM {TABLE_NAME} WHERE doc_id = :doc_id"),
                {"doc_id": doc_id},
            )
            return result.rowcount

    def get_vector_store(self):
        return self.vector_store
```

**Step 2: 검증 (Python 서버 기동 후)**

PGVector에 test-delete-001 doc_id가 있다면:
```bash
python -c "
import asyncio, os, sys
sys.path.insert(0, 'src')
from dotenv import load_dotenv; load_dotenv()
from embeddings import EmbeddingModel
from vector_store import VectorStoreManager

async def test():
    db = os.getenv('DB_CONNECTION', 'postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db')
    emb = EmbeddingModel().get_embeddings()
    mgr = await VectorStoreManager.create(db, emb)
    # 존재하지 않는 doc_id 삭제 시 0 반환 확인
    n = await mgr.delete_by_doc_id('nonexistent-id-000')
    print(f'삭제된 청크 수: {n}')  # 0이어야 함
    assert n == 0
    print('검증 통과')

asyncio.run(test())
"
```

**Step 3: Commit**

```bash
git add src/vector_store.py
git commit -m "feat(python): VectorStoreManager.delete_by_doc_id() 추가"
```

---

## Task 5: server.py — DELETE /internal/delete/{doc_id} 추가

**Files:**
- Modify: `server.py` (프로젝트 루트)

**Step 1: CORS에 DELETE 메서드 추가**

`server.py`에서 CORSMiddleware 설정을 찾아 수정:

```python
# 변경 전
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 변경 후
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

**Step 2: DeleteResponse 모델과 엔드포인트 추가**

`server.py`의 `ChatResponse` 클래스 아래에 추가:

```python
class DeleteResponse(BaseModel):
    doc_id: str
    deleted_chunks: int
```

그리고 `/internal/health` 엔드포인트 아래에 추가:

```python
@app.delete("/internal/delete/{doc_id}", response_model=DeleteResponse)
async def delete_vectors(doc_id: str):
    """Spring에서 문서 삭제 시 호출. PGVector에서 해당 doc_id의 모든 청크를 삭제한다."""
    try:
        deleted_count = await vector_store_manager.delete_by_doc_id(doc_id)
        logger.info("[delete] 벡터 삭제 완료: doc_id=%s, chunks=%d", doc_id, deleted_count)
        return DeleteResponse(doc_id=doc_id, deleted_chunks=deleted_count)
    except Exception:
        logger.error("[delete] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"벡터 삭제 실패: doc_id={doc_id}")
```

**Step 3: 서버 기동 및 검증**

```bash
uvicorn server:app --reload --port 8000
```

```bash
# 존재하지 않는 ID 삭제 테스트 (0 반환)
curl -X DELETE http://localhost:8000/internal/delete/nonexistent-id-000
# Expected: {"doc_id":"nonexistent-id-000","deleted_chunks":0}

# 헬스 체크
curl http://localhost:8000/internal/health
# Expected: {"status":"ok"}
```

**Step 4: Commit**

```bash
git add server.py
git commit -m "feat(python): DELETE /internal/delete/{doc_id} 엔드포인트 추가"
```

---

## Task 6: DocumentService.java — Python 벡터 삭제 호출 추가

**Files:**
- Modify: `backend/src/main/java/com/ncs/backend/service/DocumentService.java`

**Step 1: delete() 메서드 수정**

현재 `delete()` 메서드:
```java
public void delete(String docId) throws IOException {
    Document doc = documentMapper.findById(docId);
    if (doc != null) {
        Path uploadPath = Paths.get(uploadDir).toAbsolutePath();
        Path filePath = uploadPath.resolve(docId + "_" + doc.getFilename());
        Files.deleteIfExists(filePath);
    }
    documentMapper.delete(docId);
}
```

아래로 교체 (IOException을 내부에서 처리하도록 변경):

```java
public void delete(String docId) {
    // 1. Python PGVector 벡터 삭제 (best-effort — 실패해도 Oracle 삭제 진행)
    try {
        pythonRestClient.delete()
                .uri("/internal/delete/{docId}", docId)
                .retrieve()
                .toBodilessEntity();
        log.info("[DocumentService] PGVector 벡터 삭제 완료: docId={}", docId);
    } catch (Exception e) {
        log.warn("[DocumentService] Python 벡터 삭제 실패 (Oracle 삭제 계속 진행): docId={}, error={}",
                docId, e.getMessage());
    }

    // 2. 파일 시스템에서 삭제
    Document doc = documentMapper.findById(docId);
    if (doc != null) {
        try {
            Path uploadPath = Paths.get(uploadDir).toAbsolutePath();
            Path filePath = uploadPath.resolve(docId + "_" + doc.getFilename());
            Files.deleteIfExists(filePath);
            log.info("[DocumentService] 파일 삭제 완료: {}", filePath);
        } catch (IOException e) {
            log.warn("[DocumentService] 파일 삭제 실패 (Oracle 삭제 계속 진행): {}", e.getMessage());
        }
    }

    // 3. Oracle에서 삭제
    documentMapper.delete(docId);
    log.info("[DocumentService] Oracle 삭제 완료: docId={}", docId);
}
```

**중요:** `throws IOException`이 제거되므로 import 목록에서 `java.io.IOException`을 유지하되 메서드 시그니처에서 제거한다. `DocumentController`는 변경 불필요.

**Step 2: Spring 서버 재기동 후 전체 흐름 테스트**

Python 서버와 Spring 서버 모두 기동 후 테스트:

```bash
# 1. 문서 업로드 (INDEXED 상태 확인)
curl -X POST http://localhost:8080/api/documents \
  -F "file=@assets/실습\ NCS파일/정보기술개발/SW아키텍쳐/LM2001020101_SW아키텍처수행관리.pdf" \
  -F "mainCategory=정보기술개발" \
  -F "subCategory=SW아키텍쳐"
# Expected: {"docId":"...","status":"INDEXED",...}

# 응답에서 docId 복사 후:
DOC_ID="위에서-받은-docId"

# 2. 문서 삭제
curl -X DELETE http://localhost:8080/api/documents/$DOC_ID
# Expected: 204 No Content

# 3. Python PGVector에서 벡터 삭제 확인
curl -X DELETE http://localhost:8000/internal/delete/$DOC_ID
# Expected: {"doc_id":"...","deleted_chunks":0}  ← 이미 삭제됐으므로 0
```

**Step 3: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/service/DocumentService.java
git commit -m "feat(spring): 문서 삭제 시 Python PGVector 벡터 동시 삭제 연동"
```

---

## Task 7: ncsApi.js — 문서 API 메서드 추가

**Files:**
- Modify: `frontend/src/api/ncsApi.js`

**Step 1: fetchDocuments, uploadDocument, deleteDocument 추가**

현재 파일 말미에 아래 함수들을 추가:

```javascript
export async function fetchDocuments() {
  const res = await fetch(`${BASE_URL}/api/documents`)
  if (!res.ok) throw new Error(`Server error: ${res.status}`)
  return res.json()
}

export async function uploadDocument(file, mainCategory, subCategory) {
  const formData = new FormData()
  formData.append('file', file)
  if (mainCategory) formData.append('mainCategory', mainCategory)
  if (subCategory) formData.append('subCategory', subCategory)

  const res = await fetch(`${BASE_URL}/api/documents`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return res.json()
}

export async function deleteDocument(docId) {
  const res = await fetch(`${BASE_URL}/api/documents/${docId}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`)
  return true
}
```

**Step 2: 검증 (브라우저 콘솔)**

```javascript
// 브라우저 개발자 도구 콘솔에서:
import('/src/api/ncsApi.js').then(api => api.fetchDocuments()).then(console.log)
// Expected: 문서 배열 출력
```

**Step 3: Commit**

```bash
git add frontend/src/api/ncsApi.js
git commit -m "feat(frontend): ncsApi.js에 fetchDocuments, uploadDocument, deleteDocument 추가"
```

---

## Task 8: DocumentView.vue — 문서 관리 컴포넌트 신규 생성

**Files:**
- Create: `frontend/src/components/DocumentView.vue`

**Step 1: DocumentView.vue 전체 작성**

```vue
<script setup>
import { ref, computed, onMounted } from 'vue'
import { fetchDocuments, uploadDocument, deleteDocument } from '../api/ncsApi.js'

const props = defineProps({
  categories: {
    type: Object,
    default: () => ({}),
  },
})

// ── 상태 ─────────────────────────────────────────────────────
const documents = ref([])
const isLoading = ref(false)
const isUploading = ref(false)
const uploadError = ref('')
const uploadSuccess = ref('')

// 업로드 폼 상태
const selectedFile = ref(null)
const fileInputRef = ref(null)
const selectedMainCategory = ref('')
const selectedSubCategory = ref('')

// ── 계산 속성 ─────────────────────────────────────────────────
const mainCategories = computed(() => Object.keys(props.categories))
const subCategories = computed(() => {
  if (!selectedMainCategory.value) return []
  return props.categories[selectedMainCategory.value] || []
})

// ── 수명주기 ─────────────────────────────────────────────────
onMounted(loadDocuments)

// ── 메서드 ───────────────────────────────────────────────────
async function loadDocuments() {
  isLoading.value = true
  try {
    documents.value = await fetchDocuments()
  } catch (e) {
    console.error('문서 목록 조회 실패:', e)
  } finally {
    isLoading.value = false
  }
}

function onFileChange(e) {
  selectedFile.value = e.target.files[0] || null
  uploadError.value = ''
  uploadSuccess.value = ''
}

function onMainCategoryChange() {
  selectedSubCategory.value = ''
}

async function handleUpload() {
  if (!selectedFile.value) {
    uploadError.value = '파일을 선택해주세요.'
    return
  }
  uploadError.value = ''
  uploadSuccess.value = ''
  isUploading.value = true
  try {
    const doc = await uploadDocument(
      selectedFile.value,
      selectedMainCategory.value || null,
      selectedSubCategory.value || null,
    )
    uploadSuccess.value = `"${doc.filename}" 등록 완료 (상태: ${statusLabel(doc.status)})`
    // 폼 초기화
    selectedFile.value = null
    selectedMainCategory.value = ''
    selectedSubCategory.value = ''
    if (fileInputRef.value) fileInputRef.value.value = ''
    await loadDocuments()
  } catch (e) {
    uploadError.value = '업로드에 실패했습니다. 서버 상태를 확인해주세요.'
  } finally {
    isUploading.value = false
  }
}

async function handleDelete(docId, filename) {
  if (!confirm(`"${filename}" 문서를 삭제하시겠습니까?\nOracle과 벡터 데이터가 모두 삭제됩니다.`)) return
  try {
    await deleteDocument(docId)
    documents.value = documents.value.filter((d) => d.docId !== docId)
  } catch (e) {
    alert('삭제에 실패했습니다.')
  }
}

function statusLabel(status) {
  const labels = { INDEXED: '인덱싱 완료', PENDING: '처리 중', FAILED: '실패' }
  return labels[status] || status
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('ko-KR')
}
</script>

<template>
  <div class="doc-view">
    <!-- 업로드 섹션 -->
    <section class="upload-section">
      <h2 class="section-title">PDF 문서 등록</h2>
      <div class="upload-form">
        <label class="file-label">
          <input
            ref="fileInputRef"
            type="file"
            accept=".pdf"
            class="file-input"
            @change="onFileChange"
          />
          <span class="file-name">{{ selectedFile ? selectedFile.name : '파일 선택 (.pdf)' }}</span>
        </label>

        <select
          v-model="selectedMainCategory"
          class="cat-select"
          @change="onMainCategoryChange"
        >
          <option value="">메인 카테고리 선택</option>
          <option v-for="cat in mainCategories" :key="cat" :value="cat">{{ cat }}</option>
        </select>

        <select
          v-model="selectedSubCategory"
          class="cat-select"
          :disabled="!selectedMainCategory"
        >
          <option value="">서브 카테고리 선택</option>
          <option v-for="sub in subCategories" :key="sub" :value="sub">{{ sub }}</option>
        </select>

        <button class="upload-btn" :disabled="isUploading" @click="handleUpload">
          {{ isUploading ? '등록 중...' : '등록' }}
        </button>
      </div>

      <p v-if="uploadError" class="msg-error">{{ uploadError }}</p>
      <p v-if="uploadSuccess" class="msg-success">{{ uploadSuccess }}</p>
    </section>

    <!-- 문서 목록 섹션 -->
    <section class="list-section">
      <div class="list-header">
        <h2 class="section-title">등록된 문서 목록</h2>
        <button class="refresh-btn" :disabled="isLoading" @click="loadDocuments">
          ↺ 새로고침
        </button>
      </div>

      <div v-if="isLoading" class="state-msg">로딩 중...</div>
      <div v-else-if="documents.length === 0" class="state-msg">등록된 문서가 없습니다.</div>
      <table v-else class="doc-table">
        <thead>
          <tr>
            <th>파일명</th>
            <th>메인 카테고리</th>
            <th>서브 카테고리</th>
            <th>등록일</th>
            <th>상태</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in documents" :key="doc.docId">
            <td class="col-filename">{{ doc.filename }}</td>
            <td>{{ doc.mainCategory || '-' }}</td>
            <td>{{ doc.subCategory || '-' }}</td>
            <td>{{ formatDate(doc.uploadDate) }}</td>
            <td>
              <span :class="['status-badge', doc.status?.toLowerCase()]">
                {{ statusLabel(doc.status) }}
              </span>
            </td>
            <td>
              <button class="del-btn" @click="handleDelete(doc.docId, doc.filename)">삭제</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<style scoped>
.doc-view {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  padding: 2rem;
  height: 100%;
  overflow-y: auto;
  color: var(--text-primary, #e2e8f0);
}

/* ── 섹션 공통 ── */
.section-title {
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent, #00e5c8);
  margin-bottom: 1rem;
}

/* ── 업로드 폼 ── */
.upload-section {
  background: var(--bg-secondary, rgba(255,255,255,0.04));
  border: 1px solid var(--border, rgba(255,255,255,0.08));
  border-radius: 8px;
  padding: 1.5rem;
}

.upload-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}

.file-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(0,229,200,0.05);
  border: 1px solid var(--border, rgba(255,255,255,0.12));
  border-radius: 6px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  transition: border-color 0.2s;
  min-width: 220px;
}
.file-label:hover { border-color: var(--accent, #00e5c8); }

.file-input {
  display: none;
}

.file-name {
  font-size: 0.85rem;
  color: var(--text-secondary, #94a3b8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.cat-select {
  background: var(--bg-secondary, #1e293b);
  border: 1px solid var(--border, rgba(255,255,255,0.12));
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  color: var(--text-primary, #e2e8f0);
  font-size: 0.85rem;
  cursor: pointer;
}
.cat-select:disabled { opacity: 0.4; cursor: not-allowed; }
.cat-select:focus { outline: 1px solid var(--accent, #00e5c8); }

.upload-btn {
  background: var(--accent, #00e5c8);
  color: #0f172a;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1.5rem;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  transition: opacity 0.2s;
}
.upload-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.upload-btn:hover:not(:disabled) { opacity: 0.85; }

.msg-error { color: #f87171; font-size: 0.85rem; margin-top: 0.5rem; }
.msg-success { color: #4ade80; font-size: 0.85rem; margin-top: 0.5rem; }

/* ── 문서 목록 ── */
.list-section {
  flex: 1;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.refresh-btn {
  background: transparent;
  border: 1px solid var(--border, rgba(255,255,255,0.12));
  border-radius: 6px;
  color: var(--text-secondary, #94a3b8);
  padding: 0.35rem 0.85rem;
  font-size: 0.8rem;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}
.refresh-btn:hover:not(:disabled) {
  border-color: var(--accent, #00e5c8);
  color: var(--accent, #00e5c8);
}
.refresh-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.state-msg {
  color: var(--text-secondary, #94a3b8);
  font-size: 0.9rem;
  padding: 2rem 0;
  text-align: center;
}

.doc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.doc-table th {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid var(--border, rgba(255,255,255,0.08));
  color: var(--text-secondary, #94a3b8);
  font-weight: 500;
  letter-spacing: 0.04em;
}
.doc-table td {
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  color: var(--text-primary, #e2e8f0);
  vertical-align: middle;
}
.doc-table tr:hover td { background: rgba(255,255,255,0.03); }

.col-filename {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 상태 배지 ── */
.status-badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.status-badge.indexed { background: rgba(74,222,128,0.15); color: #4ade80; }
.status-badge.pending { background: rgba(250,204,21,0.15); color: #facc15; }
.status-badge.failed  { background: rgba(248,113,113,0.15); color: #f87171; }

/* ── 삭제 버튼 ── */
.del-btn {
  background: transparent;
  border: 1px solid rgba(248,113,113,0.4);
  border-radius: 4px;
  color: #f87171;
  padding: 0.25rem 0.65rem;
  font-size: 0.75rem;
  cursor: pointer;
  transition: background 0.2s;
}
.del-btn:hover { background: rgba(248,113,113,0.1); }
</style>
```

**Step 2: Commit**

```bash
git add frontend/src/components/DocumentView.vue
git commit -m "feat(frontend): DocumentView.vue 신규 생성 (PDF 업로드 + 목록 + 삭제)"
```

---

## Task 9: App.vue — 상단 탭 바 추가

**Files:**
- Modify: `frontend/src/App.vue`

**Step 1: App.vue 전체 교체**

```vue
<script setup>
import { ref, onMounted } from 'vue'
import FilterPanel from './components/FilterPanel.vue'
import ChatView from './components/ChatView.vue'
import DocumentView from './components/DocumentView.vue'
import { healthCheck, fetchCategories } from './api/ncsApi.js'

const isConnected = ref(false)
const sidebarOpen = ref(true)
const categories = ref({})
const activeTab = ref('chat')   // 'chat' | 'documents'

onMounted(async () => {
  isConnected.value = await healthCheck()
  if (isConnected.value) {
    try {
      categories.value = await fetchCategories()
    } catch {
      categories.value = {}
    }
  }
})

const activeFilter = ref({ mainCategory: null, subCategory: null })

function onFilterChange(mainCat, subCat) {
  activeFilter.value = { mainCategory: mainCat, subCategory: subCat }
}

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}
</script>

<template>
  <div class="app-shell">
    <div class="bg-grid" />
    <div class="bg-glow" />

    <!-- 상단 탭 바 -->
    <nav class="tab-bar">
      <button
        :class="['tab-btn', { active: activeTab === 'chat' }]"
        @click="activeTab = 'chat'"
      >
        대화
      </button>
      <button
        :class="['tab-btn', { active: activeTab === 'documents' }]"
        @click="activeTab = 'documents'"
      >
        문서 관리
      </button>
    </nav>

    <!-- 탭 콘텐츠 -->
    <div class="tab-content">
      <!-- 대화 탭 -->
      <template v-if="activeTab === 'chat'">
        <FilterPanel
          :categories="categories"
          :activeFilter="activeFilter"
          :isConnected="isConnected"
          :isOpen="sidebarOpen"
          @filter-change="onFilterChange"
          @toggle="toggleSidebar"
        />
        <main class="main-area">
          <ChatView
            :isConnected="isConnected"
            :activeFilter="activeFilter"
          />
        </main>
      </template>

      <!-- 문서 관리 탭 -->
      <template v-else-if="activeTab === 'documents'">
        <main class="main-area full-width">
          <DocumentView :categories="categories" />
        </main>
      </template>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  position: relative;
  overflow: hidden;
}

.bg-grid {
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 229, 200, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 229, 200, 0.03) 1px, transparent 1px);
  background-size: 48px 48px;
  pointer-events: none;
  z-index: 0;
}

.bg-glow {
  position: fixed;
  top: -30%;
  right: -10%;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(0, 229, 200, 0.06) 0%, transparent 70%);
  pointer-events: none;
  z-index: 0;
}

/* ── 탭 바 ── */
.tab-bar {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 0 1.5rem;
  height: 44px;
  background: var(--bg-primary, #0f172a);
  border-bottom: 1px solid rgba(255,255,255,0.08);
  position: relative;
  z-index: 10;
  flex-shrink: 0;
}

.tab-btn {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary, #94a3b8);
  font-size: 0.85rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  padding: 0 1.25rem;
  height: 100%;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}
.tab-btn:hover { color: var(--text-primary, #e2e8f0); }
.tab-btn.active {
  color: var(--accent, #00e5c8);
  border-bottom-color: var(--accent, #00e5c8);
}

/* ── 탭 콘텐츠 ── */
.tab-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
  z-index: 1;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.main-area.full-width {
  width: 100%;
}
</style>
```

**Step 2: 프론트엔드 기동 및 시각 검증**

```bash
cd frontend && npm run dev
```

브라우저에서 `http://localhost:5174` 접속 후 확인:

1. 상단에 `대화` / `문서 관리` 탭 바 표시됨
2. `대화` 탭: 기존 사이드바 + 채팅 화면 정상 동작
3. `문서 관리` 탭: PDF 업로드 폼 + 문서 목록 표시됨
4. `문서 관리` → PDF 업로드 → 목록에서 INDEXED 상태 확인
5. `문서 관리` → 삭제 버튼 → 확인 다이얼로그 → 목록에서 제거 확인

**Step 3: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat(frontend): 상단 탭 바 추가 (대화 / 문서 관리 탭 분리)"
```

---

## Task 10: 전체 통합 검증 및 최종 커밋

**Step 1: 전체 시스템 기동**

```bash
# 1. Redis (이미 실행 중 아니면)
docker start redis

# 2. 초기 프롬프트 등록
cd /c/study/langchain_study/3_playground/ncs_rag_chatbot
source venv/Scripts/activate
python src/init_prompts.py

# 3. Python AI 서버
uvicorn server:app --reload --port 8000

# 4. Spring 서버 (별도 터미널)
cd backend && ./mvnw spring-boot:run

# 5. 프론트엔드 (별도 터미널)
cd frontend && npm run dev
```

**Step 2: 검증 체크리스트**

```
□ redis-cli keys "prompt:*" → 5개 키 출력
□ redis-cli get "prompt:answer_format_prompt" → 마크다운 지침 텍스트 출력
□ curl http://localhost:8000/internal/health → {"status":"ok"}
□ 브라우저 http://localhost:5174:
    □ 상단 탭 바 "대화" / "문서 관리" 표시
    □ "대화" 탭 → 필터 + 채팅 UI 정상
    □ "문서 관리" 탭 → 업로드 폼 + 빈 목록 표시
□ PDF 업로드 테스트:
    □ 문서 관리 탭에서 PDF 선택 + 카테고리 선택 + 등록
    □ 목록에 INDEXED 상태로 표시됨
□ 채팅 테스트:
    □ 대화 탭에서 카테고리 선택 후 질문 전송
    □ 답변에 마크다운 형식 + 출처 표시됨
□ 삭제 테스트:
    □ 문서 관리 탭에서 문서 삭제
    □ Oracle + PGVector + 파일 모두 삭제 확인
```

**Step 3: 최종 커밋**

```bash
git add .
git commit -m "feat: Redis 5 prompts / 탭 UI / 삭제 일관성 전체 구현 완료"
```

---

## 파일 변경 요약

| 파일 | 작업 | Task |
|------|------|------|
| `src/init_prompts.py` | 5개 프롬프트 등록으로 확장 | 1 |
| `src/prompt_loader.py` | fallback 5개 추가 | 2 |
| `src/agent.py` | `_build_system_prompt()` 추가 | 3 |
| `src/vector_store.py` | `delete_by_doc_id()` 추가 | 4 |
| `server.py` | `DELETE /internal/delete/{doc_id}` 추가, CORS 수정 | 5 |
| `backend/.../DocumentService.java` | `delete()` Python 호출 추가 | 6 |
| `frontend/src/api/ncsApi.js` | `fetchDocuments`, `uploadDocument`, `deleteDocument` 추가 | 7 |
| `frontend/src/components/DocumentView.vue` | **신규** 문서 관리 컴포넌트 | 8 |
| `frontend/src/App.vue` | 탭 바 추가, DocumentView 통합 | 9 |
