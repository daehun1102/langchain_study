# NCS 피드백 채팅 전환 설계

**Date:** 2026-02-25
**Status:** Approved

## 목표

기존 FeedbackView의 단발성(입력 → 단일 응답) 방식을 ChatView 스타일의 대화형 채팅으로 전환한다.
`thread_id`를 활용해 세션별 독립적인 LangGraph 대화 이력을 유지한다.

---

## 데이터 흐름

```
[FeedbackView.vue]
  useFeedbackChat composable
  thread_id: UUID (마운트 시 생성, "새 대화" 버튼으로 갱신)

      ↕ sendFeedbackChat(query, threadId)  [ncsApi.js]

[Spring POST /api/chat]
  ChatRequest: { query, mainCategory, subCategory, threadId? }
  ChatService → InternalChatRequest: { query, docIds, threadId }

      ↕ POST /internal/chat

[Python FastAPI]
  기존 thread_id 지원 그대로 사용 (수정 불필요)
  InMemorySaver가 thread_id별 대화 이력 유지

[ChatResponse]
  { answer, sources }  — sources는 백엔드에서 계속 반환하나 FeedbackView에서 표시하지 않음
```

---

## 변경 파일 목록

### Frontend

| 파일 | 변경 |
|------|------|
| `frontend/src/composables/useFeedbackChat.js` | **신규** — thread_id 관리 + 채팅 로직 |
| `frontend/src/components/FeedbackView.vue` | **전면 재작성** — 채팅 UI, sources 표시 제거 |
| `frontend/src/api/ncsApi.js` | **추가** — `sendFeedbackChat(query, threadId)` |

### Backend (Spring)

| 파일 | 변경 |
|------|------|
| `ChatRequest.java` | `threadId` 필드 추가 (nullable) |
| `InternalChatRequest.java` | `threadId` 필드 + `@JsonProperty("thread_id")` |
| `ChatService.java` | `InternalChatRequest` 생성 시 `threadId` 전달 |

### AI Server (Python)

수정 없음. `server.py`가 이미 `thread_id`를 `configurable`로 처리함.

---

## useFeedbackChat 설계

```js
// frontend/src/composables/useFeedbackChat.js
export function useFeedbackChat() {
  const messages = ref([])
  const isLoading = ref(false)
  const threadId = ref(crypto.randomUUID())

  function resetThread() {
    threadId.value = crypto.randomUUID()
    messages.value = []
  }

  async function sendMessage(text) {
    // user 메시지 push → sendFeedbackChat(text, threadId.value) 호출
    // assistant 메시지 push (sources 제외 or 빈 배열)
  }

  return { messages, isLoading, threadId, resetThread, sendMessage }
}
```

---

## FeedbackView UI 구조

```
┌─────────────────────────────────────────────┐
│  NCS 과제 피드백              [새 대화]       │  ← 헤더
├─────────────────────────────────────────────┤
│  [WelcomeMessage 또는 메시지 목록]            │
│  [TypingIndicator]                          │
├─────────────────────────────────────────────┤
│  [ChatInput 재사용]                          │
└─────────────────────────────────────────────┘
```

- 재사용 컴포넌트: `MessageBubble`, `ChatInput`, `TypingIndicator`
- `MessageBubble`에 `sources: []` 전달 → sources 섹션 자동 숨김
- "새 대화" 버튼 → `resetThread()` 호출

---

## Spring 변경 세부

### ChatRequest.java
```java
@Data
public class ChatRequest {
    private String query;
    private String mainCategory;
    private String subCategory;
    private String threadId;  // nullable, 없으면 ChatService에서 "default" 사용
}
```

### InternalChatRequest.java
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

### ChatService.java
```java
String threadId = req.getThreadId() != null ? req.getThreadId() : "default";
InternalChatRequest internalReq = new InternalChatRequest(req.getQuery(), docIds, threadId);
```

---

## 제약 사항

- `InMemorySaver`는 AI 서버 재시작 시 초기화됨 (세션 지속성 없음, 현재 요구사항 범위 내)
- RAG agent 동작 유지: `rag_agent.py`, `rag_tool.py` 수정 없음
- sources API 응답은 그대로 유지, UI에서만 미표시
