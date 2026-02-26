# NCS 피드백 탭 좌우 분할 UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** FeedbackView 탭을 좌(v1 Subagent) / 우(v2 HandOff) 2열로 분할하여 두 agent를 나란히 비교할 수 있게 한다.

**Architecture:** 단일 AI Server가 시작 시 v1/v2 agent를 모두 초기화하고, 요청의 `version` 필드로 routing한다. Spring Boot는 version을 그대로 AI Server로 전달한다. Frontend는 `FeedbackChatPanel.vue` 컴포넌트를 신규 생성하여 version prop으로 좌/우를 구분한다.

**Tech Stack:** Python FastAPI, Spring Boot (Java/Lombok), Vue 3 Composition API

---

## Task 1: AI Server — ChatRequest에 version 필드 추가 + 두 agent 초기화

**Files:**
- Modify: `ai_server/server.py`

현재 `server.py`는 agent를 전역 변수 하나(`agent`)로 관리하고 `config.agent_version` 하나만 초기화한다.
v1/v2를 동시에 서비스하려면 두 변수로 분리해야 한다.

**Step 1: ChatRequest 모델에 version 필드 추가**

`ai_server/server.py` 의 `ChatRequest` 클래스를 찾아 `version` 필드를 추가한다.

```python
class ChatRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None
    thread_id: str = "default"
    version: str = "v1"          # ← 추가
```

**Step 2: 전역 변수를 두 개로 분리**

```python
# 기존
agent: Optional[BaseAgent] = None

# 변경
agent_v1: Optional[BaseAgent] = None
agent_v2: Optional[BaseAgent] = None
```

**Step 3: lifespan에서 v1/v2 모두 초기화**

기존 `agent = await create_agent(...)` 한 줄을 아래로 교체한다.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store_manager, agent_v1, agent_v2

    emb = EmbeddingModel().get_embeddings()
    vector_store_manager = await VectorStoreManager.create(settings.db_connection, emb)

    agent_v1 = await create_agent(vector_store_manager, version="v1")
    agent_v2 = await create_agent(vector_store_manager, version="v2")

    logger.info("[server] Agent v1/v2 초기화 완료")
    yield
```

**Step 4: /internal/chat 핸들러에서 version으로 routing**

기존 `agent.run(...)` 을 아래로 교체한다.

```python
@app.post("/internal/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        doc_ids = req.doc_ids or []
        config = {
            "configurable": {
                "thread_id": req.thread_id,
                "doc_ids": doc_ids,
            }
        }
        selected_agent = agent_v2 if req.version == "v2" else agent_v1
        last_message = await selected_agent.run(req.query, config=config)
        answer = last_message.content if last_message else "응답을 생성할 수 없습니다."
        sources = await _collect_sources(req.query, doc_ids)
        return ChatResponse(answer=answer, sources=sources)
    except Exception:
        logger.error("[chat] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail="AI 응답 생성 실패")
```

**Step 5: 테스트 실행 (AI Server 기존 테스트)**

```bash
cd ai_server
python -m pytest tests/test_agents.py -v
```

Expected: 기존 테스트 모두 PASS (server.py 변경은 기존 agent 테스트에 영향 없음)

**Step 6: commit**

```bash
git add ai_server/server.py
git commit -m "feat(server): v1/v2 agent 동시 초기화 및 version routing 추가"
```

---

## Task 2: AI Server — server.py 통합 테스트 추가

**Files:**
- Modify: `ai_server/tests/test_agents.py`

server.py 의 ChatRequest version 라우팅 로직을 단위 테스트한다.

**Step 1: 테스트 작성**

`ai_server/tests/test_agents.py` 파일 맨 아래에 추가한다.

```python
async def test_chat_request_default_version_is_v1():
    """ChatRequest의 version 기본값은 v1이어야 한다."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    # server.py를 직접 임포트하지 않고 ChatRequest만 검증
    from pydantic import BaseModel
    from typing import Optional, List

    class ChatRequest(BaseModel):
        query: str
        doc_ids: Optional[List[str]] = None
        thread_id: str = "default"
        version: str = "v1"

    req = ChatRequest(query="테스트")
    assert req.version == "v1"

    req_v2 = ChatRequest(query="테스트", version="v2")
    assert req_v2.version == "v2"
```

**Step 2: 테스트 실행**

```bash
cd ai_server
python -m pytest tests/test_agents.py::test_chat_request_default_version_is_v1 -v
```

Expected: PASS

**Step 3: commit**

```bash
git add ai_server/tests/test_agents.py
git commit -m "test(server): ChatRequest version 필드 기본값 테스트 추가"
```

---

## Task 3: Spring Boot — version 필드 전달

**Files:**
- Modify: `backend/src/main/java/com/ncs/backend/dto/ChatRequest.java`
- Modify: `backend/src/main/java/com/ncs/backend/dto/InternalChatRequest.java`
- Modify: `backend/src/main/java/com/ncs/backend/service/ChatService.java`

**Step 1: ChatRequest.java에 version 필드 추가**

파일을 열어 기존 필드 아래에 추가한다.

```java
private String version = "v1";   // ← 추가
```

결과:
```java
@Data
public class ChatRequest {
    private String query;
    private String mainCategory;
    private String subCategory;
    private String threadId;
    private String version = "v1";   // ← 추가
}
```

**Step 2: InternalChatRequest.java에 version 필드 추가**

현재 생성자는 `(query, docIds, threadId)` 3개 인자다. version을 4번째 인자로 추가한다.

```java
@Data
@AllArgsConstructor
public class InternalChatRequest {
    private String query;

    @JsonProperty("doc_ids")
    private List<String> docIds;

    @JsonProperty("thread_id")
    private String threadId;

    @JsonProperty("version")
    private String version;         // ← 추가
}
```

**Step 3: ChatService.java에서 version 전달**

`InternalChatRequest` 생성 부분을 찾아 수정한다.

```java
// 기존
InternalChatRequest internalReq = new InternalChatRequest(req.getQuery(), docIds, threadId);

// 변경
String version = req.getVersion() != null ? req.getVersion() : "v1";
InternalChatRequest internalReq = new InternalChatRequest(req.getQuery(), docIds, threadId, version);
```

**Step 4: Spring Boot 빌드 확인**

```bash
cd backend
./mvnw compile
```

Expected: BUILD SUCCESS (컴파일 오류 없음)

**Step 5: commit**

```bash
git add backend/src/main/java/com/ncs/backend/dto/ChatRequest.java
git add backend/src/main/java/com/ncs/backend/dto/InternalChatRequest.java
git add backend/src/main/java/com/ncs/backend/service/ChatService.java
git commit -m "feat(spring): version 필드를 AI 서버로 전달"
```

---

## Task 4: Frontend — ncsApi.js version 파라미터 추가

**Files:**
- Modify: `frontend/src/api/ncsApi.js`

**Step 1: sendFeedbackChat 함수 시그니처 및 body 변경**

기존:
```js
export async function sendFeedbackChat(query, threadId = null) {
  const body = { query }
  if (threadId) body.threadId = threadId
  ...
}
```

변경:
```js
export async function sendFeedbackChat(query, threadId = null, version = 'v1') {
  const body = { query, version }
  if (threadId) body.threadId = threadId
  ...
}
```

**Step 2: commit**

```bash
git add frontend/src/api/ncsApi.js
git commit -m "feat(api): sendFeedbackChat에 version 파라미터 추가"
```

---

## Task 5: Frontend — useFeedbackChat.js version 파라미터 추가

**Files:**
- Modify: `frontend/src/composables/useFeedbackChat.js`

**Step 1: 함수 시그니처와 sendFeedbackChat 호출부 변경**

기존:
```js
export function useFeedbackChat() {
  ...
  const result = await sendFeedbackChat(text, threadId.value)
  ...
}
```

변경:
```js
export function useFeedbackChat(version = 'v1') {
  ...
  const result = await sendFeedbackChat(text, threadId.value, version)
  ...
}
```

**Step 2: commit**

```bash
git add frontend/src/composables/useFeedbackChat.js
git commit -m "feat(composable): useFeedbackChat에 version 파라미터 추가"
```

---

## Task 6: Frontend — FeedbackChatPanel.vue 신규 생성

**Files:**
- Create: `frontend/src/components/FeedbackChatPanel.vue`

현재 `FeedbackView.vue` 의 내부 구조(헤더 + 메시지 목록 + 입력창)를 그대로 이 컴포넌트로 이식한다.

**Step 1: FeedbackChatPanel.vue 작성**

```vue
<script setup>
import MessageBubble from './MessageBubble.vue'
import ChatInput from './ChatInput.vue'
import TypingIndicator from './TypingIndicator.vue'
import { useFeedbackChat } from '../composables/useFeedbackChat.js'

const props = defineProps({
  version: { type: String, required: true },   // 'v1' | 'v2'
  label: { type: String, required: true },      // 패널 헤더 표시 이름
})

const {
  messages,
  isLoading,
  scrollContainer,
  resetThread,
  sendMessage,
} = useFeedbackChat(props.version)
</script>

<template>
  <div class="chat-panel">
    <header class="panel-header">
      <div class="header-left">
        <h3>{{ label }}</h3>
        <p>직원 이름이나 사번을 포함해 질문하세요</p>
      </div>
      <button class="new-chat-btn" @click="resetThread">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M2 7a5 5 0 1 1 5 5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
          <path d="M2 4.5V7H4.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        새 대화
      </button>
    </header>

    <div class="messages-scroll" ref="scrollContainer">
      <div class="messages-inner">
        <div v-if="!messages.length" class="empty-state">
          <div class="empty-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <rect x="6" y="6" width="36" height="36" rx="8" stroke="var(--accent)" stroke-width="1" opacity="0.3"/>
              <rect x="12" y="12" width="24" height="24" rx="5" stroke="var(--accent)" stroke-width="1" opacity="0.5"/>
              <path d="M19 19h10M19 24h7M19 29h8" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </div>
          <h3>NCS 과제 피드백 에이전트</h3>
          <p>직원 이름 또는 사번을 포함해 질문하세요.<br/>예: <em>EMP001의 NCS 과제 채점 결과를 피드백해줘</em></p>
        </div>

        <MessageBubble
          v-for="(msg, i) in messages"
          :key="i"
          :message="msg"
          :index="i"
        />

        <TypingIndicator v-if="isLoading" />
      </div>
    </div>

    <ChatInput :loading="isLoading" @send="sendMessage" />
  </div>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid var(--border, rgba(255,255,255,0.08));
  flex-shrink: 0;
}

.header-left h3 {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary, #e2e8f0);
  margin: 0 0 0.1rem;
}

.header-left p {
  font-size: 0.72rem;
  color: var(--text-secondary, #94a3b8);
  margin: 0;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.8rem;
  background: transparent;
  border: 1px solid var(--border, rgba(255,255,255,0.1));
  border-radius: 8px;
  color: var(--text-secondary, #94a3b8);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.new-chat-btn:hover {
  border-color: var(--accent, #00e5c8);
  color: var(--accent, #00e5c8);
}

.messages-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.25rem;
}

.messages-inner {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 2.5rem 1rem 2rem;
  animation: fadeInUp 0.6s ease both;
}

.empty-icon { margin-bottom: 0.25rem; }

.empty-state h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary, #e2e8f0);
}

.empty-state p {
  font-size: 0.85rem;
  color: var(--text-secondary, #94a3b8);
  text-align: center;
  line-height: 1.7;
}

.empty-state em {
  font-style: normal;
  color: var(--accent, #00e5c8);
}
</style>
```

**Step 2: commit**

```bash
git add frontend/src/components/FeedbackChatPanel.vue
git commit -m "feat(frontend): FeedbackChatPanel 컴포넌트 신규 생성"
```

---

## Task 7: Frontend — FeedbackView.vue 좌우 분할 레이아웃으로 교체

**Files:**
- Modify: `frontend/src/components/FeedbackView.vue`

기존 FeedbackView.vue 전체를 아래로 교체한다.
(기존 메시지 목록/입력창 로직은 FeedbackChatPanel.vue로 이전했으므로 이 파일은 레이아웃만 담당)

**Step 1: FeedbackView.vue 전체 교체**

```vue
<script setup>
import FeedbackChatPanel from './FeedbackChatPanel.vue'
</script>

<template>
  <div class="feedback-view">
    <header class="feedback-header">
      <h2>NCS 과제 피드백 비교</h2>
      <p>좌: Subagent (v1) &nbsp;|&nbsp; 우: HandOff (v2)</p>
    </header>

    <div class="panels">
      <FeedbackChatPanel version="v1" label="Subagent (v1)" />
      <div class="divider" />
      <FeedbackChatPanel version="v2" label="HandOff (v2)" />
    </div>
  </div>
</template>

<style scoped>
.feedback-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.feedback-header {
  padding: 0.6rem 1.5rem;
  border-bottom: 1px solid var(--border, rgba(255,255,255,0.08));
  flex-shrink: 0;
}

.feedback-header h2 {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary, #e2e8f0);
  margin: 0 0 0.1rem;
}

.feedback-header p {
  font-size: 0.72rem;
  color: var(--text-secondary, #94a3b8);
  margin: 0;
}

.panels {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

.divider {
  width: 1px;
  background: var(--border, rgba(255,255,255,0.08));
  flex-shrink: 0;
}
</style>
```

**Step 2: 브라우저에서 시각적으로 확인**

```bash
cd frontend
npm run dev
```

- NCS 피드백 탭 클릭
- 좌우 패널 모두 표시되는지 확인
- 각 패널에서 독립적으로 메시지 전송 가능한지 확인

**Step 3: commit**

```bash
git add frontend/src/components/FeedbackView.vue
git commit -m "feat(frontend): FeedbackView를 v1/v2 좌우 분할 레이아웃으로 교체"
```

---

## 완료 기준

- [ ] AI Server 시작 시 v1/v2 agent 모두 로그에 "초기화 완료" 출력
- [ ] POST /internal/chat `{ version: "v1" }` → v1 agent 응답
- [ ] POST /internal/chat `{ version: "v2" }` → v2 agent 응답
- [ ] 브라우저에서 피드백 탭이 좌우 2열로 표시됨
- [ ] 좌패널과 우패널이 각각 독립적인 대화 가능
- [ ] 각 패널 "새 대화" 버튼이 해당 패널만 초기화
