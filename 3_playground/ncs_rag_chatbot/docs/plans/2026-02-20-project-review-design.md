# NCS RAG Chatbot — 프로젝트 리뷰 설계

**목적:** 주니어 개발자가 전체 프로젝트 흐름을 단계적으로 완전히 이해한다.
**방식:** 시나리오 흐름 중심 — 두 가지 핵심 사용자 시나리오를 코드 레벨로 추적한다.

---

## 섹션 1 — 전체 아키텍처 개요

- 서버가 왜 3개(Spring, Python, Frontend)인지, 각각 무엇을 책임지는지
- 데이터베이스가 왜 Oracle + PGVector로 분리되어 있는지
- `doc_id`(UUID)가 전체 시스템을 어떻게 묶는 핵심 키인지

---

## 섹션 2 — 시나리오 1: PDF 업로드 흐름 (11단계)

| 단계 | 위치 | 핵심 메서드/클래스 |
|------|------|------------------|
| 1 | Frontend | `DocumentView.vue` — 파일 선택 + 카테고리 선택 |
| 2 | Frontend | `ncsApi.js:uploadDocument()` — FormData 전송 |
| 3 | Spring | `DocumentController.upload()` — MultipartFile 수신 |
| 4 | Spring | `DocumentService.upload()` — doc_id(UUID) 발급 + 파일 저장 |
| 5 | Spring | `DocumentMapper.insert()` — Oracle `documents` 테이블 INSERT (status=PENDING) |
| 6 | Spring | `RestClient.post("/internal/ingest")` — Python으로 위임 |
| 7 | Python | `server.py:ingest()` — IngestRequest 수신 |
| 8 | Python | `ingest.py:ingest_single_document()` — 전체 파이프라인 실행 |
| 9 | Python | `DocumentLoader.load()` + `DocumentSplitter.split_documents()` — 청크 생성 |
| 10 | Python | `EmbeddingModel.get_embeddings()` — OpenAI 임베딩 |
| 11 | Python | `PGVectorStore.aadd_documents()` — PGVector 저장 + Oracle status=INDEXED 업데이트 |

---

## 섹션 3 — 시나리오 2: RAG 채팅 흐름 (12단계)

| 단계 | 위치 | 핵심 메서드/클래스 |
|------|------|------------------|
| 1 | Frontend | `ChatInput.vue` — 사용자 질문 입력 |
| 2 | Frontend | `ncsApi.js:sendChat()` — query + 카테고리 필터 전송 |
| 3 | Spring | `ChatController.chat()` — ChatRequest 수신 |
| 4 | Spring | `ChatService.chat()` — 카테고리로 Oracle 조회 |
| 5 | Spring | `DocumentMapper.findDocIdsByCategory()` — doc_id 목록 반환 |
| 6 | Spring | `RestClient.post("/internal/chat")` — query + doc_ids Python으로 위임 |
| 7 | Python | `server.py:chat()` — ChatRequest 수신 |
| 8 | Python | `ToolBuilder.build_tools(doc_ids)` — 필터된 검색 도구 생성 |
| 9 | Python | `ChatAgent.create_agent(tools)` — LangGraph ReAct Agent 구성 |
| 10 | Python | `agent.run(query)` → `retrieve_context()` — 벡터 유사도 검색 |
| 11 | Python | `VectorStoreManager.similarity_search_by_doc_ids()` — doc_id IN 필터 |
| 12 | Python | LLM 응답 생성 + `_collect_sources()` — 출처 반환 |

---

## 섹션 4 — 지원 시스템

### Redis 프롬프트 관리
- Spring `PromptController.set()` — `PUT /api/prompts/{key}` → Redis에 `prompt:<key>` 저장
- Python `prompt_loader.get_prompt()` — Redis 로드 → fallback 폴백
- `agent.py:_build_system_prompt()` — 5개 프롬프트 결합

### Arize Phoenix 트레이싱
- `tracing.py:setup_tracing()` — LangChain 자동 계측
- `server.py` 최상단 호출 — 모든 LangChain 실행 트레이싱
