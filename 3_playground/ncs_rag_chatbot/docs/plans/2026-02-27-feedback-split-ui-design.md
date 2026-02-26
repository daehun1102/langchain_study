# 설계 문서: NCS 피드백 탭 좌우 분할 UI

**날짜**: 2026-02-27
**범위**: Frontend (Vue) + Spring Boot + AI Server (FastAPI)

---

## 목표

NCS 피드백 탭을 좌우 2분할 화면으로 변경한다.
- **왼쪽**: v1 Subagent 방식 (SupervisorAgent)
- **오른쪽**: v2 HandOff 방식 (NCSHandoffAgent)
- 각 패널은 독립적인 세션(thread_id)과 메시지 목록을 가진다.

---

## 아키텍처 & 데이터 흐름

```
FeedbackView.vue
  ├─ FeedbackChatPanel.vue  (version="v1")   → 독립 thread_id
  └─ FeedbackChatPanel.vue  (version="v2")   → 독립 thread_id
          │
          ↓ sendFeedbackChat(query, threadId, version)
        ncsApi.js
          │
          ↓ POST /api/chat  { query, threadId, version }
        Spring ChatController
          │
          ↓ POST /internal/chat  { query, doc_ids, thread_id, version }
        FastAPI server.py
          ├─ version="v1" → SupervisorAgent (v1)
          └─ version="v2" → NCSHandoffAgent (v2)
```

---

## 변경 파일 목록

### Frontend (Vue)

| 파일 | 변경 내용 |
|------|-----------|
| `src/components/FeedbackView.vue` | 좌우 2열 레이아웃으로 교체. 헤더에 각 방식 이름 표시. |
| `src/components/FeedbackChatPanel.vue` | **신규 생성**. version prop 수신. 메시지 목록 + 입력창 포함. |
| `src/composables/useFeedbackChat.js` | `version` 파라미터 추가. `sendFeedbackChat` 호출 시 version 전달. |
| `src/api/ncsApi.js` | `sendFeedbackChat(query, threadId, version)` — version을 body에 추가. |

### Spring Boot

| 파일 | 변경 내용 |
|------|-----------|
| `dto/ChatRequest.java` | `version` 필드 추가 (기본값 "v1"). |
| `dto/InternalChatRequest.java` | `version` 필드 추가. |
| `service/ChatService.java` | `internalReq` 생성 시 version 포함. |

### AI Server (FastAPI)

| 파일 | 변경 내용 |
|------|-----------|
| `server.py` | 시작 시 v1/v2 agent 모두 초기화. `ChatRequest`에 version 필드 추가. `/internal/chat` 에서 version으로 agent 선택. |

---

## 컴포넌트 설계

### FeedbackView.vue (변경)

```
┌────────────────────────────────────────────────────┐
│  NCS 피드백 비교                                     │
├──────────────────────┬─────────────────────────────┤
│  Subagent (v1)  [새대화] │  HandOff (v2)  [새대화] │
├──────────────────────┼─────────────────────────────┤
│                      │                             │
│   메시지 목록         │   메시지 목록                │
│                      │                             │
├──────────────────────┼─────────────────────────────┤
│  [입력창]    [전송]   │  [입력창]    [전송]          │
└──────────────────────┴─────────────────────────────┘
```

- 레이아웃: `display: flex; flex-direction: row`
- 가운데 구분선: `1px solid var(--border)`
- 각 패널: `flex: 1; min-width: 0`

### FeedbackChatPanel.vue (신규)

props:
- `version: String` — "v1" | "v2"
- `label: String` — 패널 상단에 표시할 이름

내부: 현재 `FeedbackView.vue` 의 메시지 목록 + 헤더 + 입력창 구조를 그대로 이식.
`useFeedbackChat(version)` 컴포저블 사용.

### useFeedbackChat.js (변경)

```js
export function useFeedbackChat(version = 'v1') {
  // ...
  const result = await sendFeedbackChat(text, threadId.value, version)
  // ...
}
```

### ncsApi.js (변경)

```js
export async function sendFeedbackChat(query, threadId, version = 'v1') {
  const body = { query, version }
  if (threadId) body.threadId = threadId
  // POST /api/chat
}
```

---

## Spring Boot 변경

### ChatRequest.java

```java
private String version = "v1";  // 추가
```

### InternalChatRequest.java

```java
private String version;  // 추가 (with @JsonProperty("version"))
```

### ChatService.java

```java
InternalChatRequest internalReq = new InternalChatRequest(
    req.getQuery(), docIds, threadId, req.getVersion()
);
```

---

## AI Server 변경

### server.py

```python
# 전역 변수
agent_v1: Optional[BaseAgent] = None
agent_v2: Optional[BaseAgent] = None

# lifespan: 둘 다 초기화
agent_v1 = await create_agent(vector_store_manager, version="v1")
agent_v2 = await create_agent(vector_store_manager, version="v2")

# ChatRequest 모델
class ChatRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None
    thread_id: str = "default"
    version: str = "v1"          # 추가

# /internal/chat 핸들러
selected_agent = agent_v2 if req.version == "v2" else agent_v1
last_message = await selected_agent.run(req.query, config=config)
```

---

## 범위 외 (변경 없음)

- `MessageBubble.vue`, `TypingIndicator.vue`, `ChatInput.vue` — 재사용
- `ChatView.vue`, `DocumentView.vue` — 무관
- Spring Boot ChatController — `ChatRequest` 수신 그대로, 변경 없음
