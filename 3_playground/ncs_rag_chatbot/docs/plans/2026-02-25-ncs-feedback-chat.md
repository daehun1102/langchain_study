# NCS 피드백 채팅 전환 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** FeedbackView를 단발성 조회에서 세션별 대화형 채팅으로 전환한다.

**Architecture:** `useFeedbackChat` composable이 UUID thread_id를 관리하고, "새 대화" 버튼으로 세션을 갱신한다. thread_id는 Frontend → Spring(`/api/chat`) → Python(`/internal/chat`) 으로 전달되며, Python의 InMemorySaver가 thread_id별 대화 이력을 유지한다.

**Tech Stack:** Vue 3 Composition API, Spring Boot (RestClient), Python FastAPI (LangGraph InMemorySaver — 수정 없음)

---

## Task 1: ncsApi.js — sendFeedbackChat 함수 추가

**Files:**
- Modify: `frontend/src/api/ncsApi.js`

**배경:**
기존 `sendChat(query, mainCategory, subCategory)`는 thread_id를 전달하지 않는다.
FeedbackView 전용으로 `sendFeedbackChat(query, threadId)`를 추가한다.
기존 `sendChat`은 수정하지 않는다.

**Step 1: `sendFeedbackChat` 함수 추가**

`frontend/src/api/ncsApi.js` 파일 끝에 다음을 추가한다:

```js
export async function sendFeedbackChat(query, threadId) {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, threadId }),
  })

  if (!res.ok) {
    throw new Error(`Server error: ${res.status}`)
  }

  return res.json()
}
```

**Step 2: 수동 확인**

브라우저 콘솔에서:
```js
import('/src/api/ncsApi.js').then(m => console.log(typeof m.sendFeedbackChat))
// 출력: "function"
```

**Step 3: Commit**

```bash
git add frontend/src/api/ncsApi.js
git commit -m "feat(api): sendFeedbackChat — thread_id 포함 피드백 전용 API 함수"
```

---

## Task 2: useFeedbackChat.js — composable 신규 작성

**Files:**
- Create: `frontend/src/composables/useFeedbackChat.js`

**배경:**
`useChat.js`와 유사한 패턴이지만 thread_id 관리와 sources 제거를 담당한다.
`crypto.randomUUID()`로 마운트 시 UUID 생성, `resetThread()`로 갱신한다.

**Step 1: composable 파일 작성**

```js
import { ref, watch, nextTick } from 'vue'
import { sendFeedbackChat } from '../api/ncsApi.js'

export function useFeedbackChat() {
  const messages = ref([])
  const isLoading = ref(false)
  const scrollContainer = ref(null)
  const threadId = ref(crypto.randomUUID())

  function resetThread() {
    threadId.value = crypto.randomUUID()
    messages.value = []
  }

  function scrollToBottom() {
    nextTick(() => {
      if (scrollContainer.value) {
        scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
      }
    })
  }

  watch(messages, scrollToBottom, { deep: true })

  async function sendMessage(text) {
    if (!text.trim() || isLoading.value) return

    messages.value.push({
      role: 'user',
      content: text,
      timestamp: Date.now(),
    })
    scrollToBottom()

    isLoading.value = true

    try {
      const result = await sendFeedbackChat(text, threadId.value)

      messages.value.push({
        role: 'assistant',
        content: result.answer,
        sources: [],          // sources 표시 안 함 (RAG는 동작, UI만 숨김)
        timestamp: Date.now(),
      })
    } catch (err) {
      messages.value.push({
        role: 'system',
        content: `서버 연결 오류: ${err.message}. 서버가 실행 중인지 확인해주세요.`,
        timestamp: Date.now(),
      })
    } finally {
      isLoading.value = false
      scrollToBottom()
    }
  }

  return {
    messages,
    isLoading,
    scrollContainer,
    threadId,
    resetThread,
    sendMessage,
  }
}
```

**Step 2: Commit**

```bash
git add frontend/src/composables/useFeedbackChat.js
git commit -m "feat(composable): useFeedbackChat — thread_id 세션 관리"
```

---

## Task 3: FeedbackView.vue — 채팅 UI로 전면 재작성

**Files:**
- Modify: `frontend/src/components/FeedbackView.vue`

**배경:**
기존: 사번 입력창 + 단일 응답 표시.
신규: ChatView와 유사한 메시지 목록 + 입력창 + "새 대화" 버튼.
`MessageBubble`에 `sources: []`를 전달하면 sources 섹션이 자동으로 숨겨진다 (`v-if="sources.length"` 조건 참조).

**Step 1: FeedbackView.vue 전체 교체**

```vue
<script setup>
import MessageBubble from './MessageBubble.vue'
import ChatInput from './ChatInput.vue'
import TypingIndicator from './TypingIndicator.vue'
import { useFeedbackChat } from '../composables/useFeedbackChat.js'

const {
  messages,
  isLoading,
  scrollContainer,
  resetThread,
  sendMessage,
} = useFeedbackChat()
</script>

<template>
  <div class="feedback-view">
    <header class="feedback-header">
      <div class="header-left">
        <h2>NCS 과제 피드백</h2>
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
.feedback-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

.feedback-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--border, rgba(255,255,255,0.08));
  flex-shrink: 0;
}

.header-left h2 {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary, #e2e8f0);
  margin: 0 0 0.1rem;
}

.header-left p {
  font-size: 0.75rem;
  color: var(--text-secondary, #94a3b8);
  margin: 0;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.9rem;
  background: transparent;
  border: 1px solid var(--border, rgba(255,255,255,0.1));
  border-radius: 8px;
  color: var(--text-secondary, #94a3b8);
  font-size: 0.78rem;
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
  padding: 1.25rem 1.5rem;
}

.messages-inner {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 3rem 1rem 2rem;
  animation: fadeInUp 0.6s ease both;
}

.empty-icon { margin-bottom: 0.25rem; }

.empty-state h3 {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--text-primary, #e2e8f0);
}

.empty-state p {
  font-size: 0.88rem;
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

**Step 2: 수동 확인**

1. 브라우저에서 NCS 피드백 탭 열기
2. "EMP001의 NCS 과제 피드백해줘" 입력 → AI 응답 확인
3. 추가 질문 입력 → 대화가 이어지는지 확인 (thread_id 유지)
4. "새 대화" 버튼 클릭 → 메시지 목록이 초기화되는지 확인
5. sources 섹션이 표시되지 않는지 확인

**Step 3: Commit**

```bash
git add frontend/src/components/FeedbackView.vue
git commit -m "feat(ui): FeedbackView 대화형 채팅으로 전환 — 새 대화 버튼 + sources 숨김"
```

---

## Task 4: InternalChatRequest.java — thread_id 필드 추가

**Files:**
- Modify: `backend/src/main/java/com/ncs/backend/dto/InternalChatRequest.java`

**배경:**
Python AI 서버의 `ChatRequest`는 이미 `thread_id`를 지원한다 (`server.py:83`).
Spring이 Python에 보낼 때 `thread_id`를 포함해야 한다.

**Step 1: InternalChatRequest.java 수정**

기존:
```java
@Data
@AllArgsConstructor
public class InternalChatRequest {
    private String query;

    @JsonProperty("doc_ids")
    private List<String> docIds;
}
```

변경 후:
```java
@Data
@AllArgsConstructor
public class InternalChatRequest {
    private String query;

    @JsonProperty("doc_ids")
    private List<String> docIds;

    @JsonProperty("thread_id")
    private String threadId;
}
```

**Step 2: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/dto/InternalChatRequest.java
git commit -m "feat(dto): InternalChatRequest thread_id 필드 추가"
```

---

## Task 5: ChatRequest.java — threadId 필드 추가

**Files:**
- Modify: `backend/src/main/java/com/ncs/backend/dto/ChatRequest.java`

**배경:**
프론트엔드가 `/api/chat` POST body에 `threadId`를 포함해 전송한다.
Spring이 이를 수신하려면 DTO에 필드가 있어야 한다.

**Step 1: ChatRequest.java 수정**

기존:
```java
@Data
public class ChatRequest {
    private String query;
    private String mainCategory;
    private String subCategory;
}
```

변경 후:
```java
@Data
public class ChatRequest {
    private String query;
    private String mainCategory;
    private String subCategory;
    private String threadId;    // nullable — 없으면 ChatService에서 "default" 사용
}
```

**Step 2: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/dto/ChatRequest.java
git commit -m "feat(dto): ChatRequest threadId 필드 추가"
```

---

## Task 6: ChatService.java — threadId 전달

**Files:**
- Modify: `backend/src/main/java/com/ncs/backend/service/ChatService.java`

**배경:**
`InternalChatRequest` 생성자에 `threadId` 인자가 추가됐다 (Task 4).
`ChatRequest.threadId`가 null이면 `"default"` fallback을 사용한다.

**Step 1: ChatService.java 수정**

기존:
```java
InternalChatRequest internalReq = new InternalChatRequest(req.getQuery(), docIds);
```

변경 후:
```java
String threadId = req.getThreadId() != null ? req.getThreadId() : "default";
InternalChatRequest internalReq = new InternalChatRequest(req.getQuery(), docIds, threadId);
```

전체 `chat` 메서드:
```java
public ChatResponse chat(ChatRequest req) {
    List<String> docIds = documentService.findDocIdsByCategory(
            req.getMainCategory(), req.getSubCategory()
    );
    log.info("[ChatService] query={}, docIds={}, threadId={}", req.getQuery(), docIds, req.getThreadId());

    String threadId = req.getThreadId() != null ? req.getThreadId() : "default";
    InternalChatRequest internalReq = new InternalChatRequest(req.getQuery(), docIds, threadId);
    ChatResponse response = pythonRestClient.post()
            .uri("/internal/chat")
            .body(internalReq)
            .retrieve()
            .body(ChatResponse.class);

    return response;
}
```

**Step 2: Spring 빌드 확인**

```bash
cd backend
./mvnw compile
# 출력: BUILD SUCCESS
```

**Step 3: 수동 E2E 확인**

AI 서버(`uvicorn server:app --reload --port 8000`)와 Spring Boot 서버 모두 기동 후:

```bash
# thread_id 포함 요청 테스트
curl -s -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"EMP001의 NCS 과제 피드백해줘","threadId":"test-session-001"}' \
  | python -m json.tool

# 같은 thread_id로 후속 질문 (대화 이력 유지 확인)
curl -s -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"방금 피드백에서 가장 부족한 부분이 어디였어?","threadId":"test-session-001"}' \
  | python -m json.tool
```

두 번째 응답이 첫 번째 피드백을 참조하면 세션이 올바르게 유지되는 것이다.

**Step 4: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/service/ChatService.java
git commit -m "feat(service): ChatService thread_id 전달 — 세션별 대화 이력 지원"
```

---

## 최종 E2E 확인

1. `ai_server/`: `uvicorn server:app --reload --port 8000`
2. `backend/`: Spring Boot 기동
3. `frontend/`: `npm run dev`
4. 브라우저 → NCS 피드백 탭 열기
5. "EMP001의 NCS 과제 피드백을 분석해줘" 입력
6. AI 응답 확인 (sources 섹션 없음)
7. "가장 취약한 역량이 뭐야?" 후속 질문 → 앞 대화 컨텍스트 참조 확인
8. "새 대화" 버튼 → 화면 초기화 후 새 thread_id로 독립 세션 시작 확인
