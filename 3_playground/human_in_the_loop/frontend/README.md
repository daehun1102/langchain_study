# FAB Control — Human-in-the-Loop Agent Frontend

반도체 FAB 공정 품질 관리를 위한 AI 에이전트 채팅 인터페이스.
LangGraph 서버와 SSE 스트리밍으로 통신하며, 에이전트의 도구 호출을 사용자가 승인/거부/수정할 수 있는 Human-in-the-Loop 워크플로우를 제공한다.

## 기술 스택

| 항목 | 버전 |
|------|------|
| Vue | 3.5 (`<script setup>` SFC) |
| Vite | 7.3 |
| marked | 17.x (마크다운 렌더링) |

## 실행

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # dist/ 에 프로덕션 빌드
```

개발 서버는 Vite proxy를 통해 `/threads`, `/assistants`, `/ok` 요청을 `http://localhost:2024` (LangGraph 서버)로 포워딩한다.
서버가 꺼져 있으면 자동으로 **데모 모드**로 전환되어 시뮬레이션 응답을 보여준다.

## 디렉토리 구조

```
src/
├── main.js                        # Vue 앱 마운트
├── App.vue                        # 루트 레이아웃 (Sidebar + ChatView)
├── api/
│   └── langgraph.js               # LangGraph REST/SSE 클라이언트
├── composables/
│   ├── useChat.js                 # 채팅 상태 관리 · 서버 통신 · HitL 핸들러
│   └── useDemoMode.js             # 데모 모드 시뮬레이션 로직
└── components/
    ├── Sidebar.vue                # 좌측 사이드바 (스레드 목록, 새 대화 생성)
    ├── ChatView.vue               # 채팅 화면 (composable 조합 + 하위 컴포넌트 배치)
    ├── ChatHeader.vue             # 상단 헤더 바 (LIVE/DEMO 배지)
    ├── ChatInput.vue              # 하단 메시지 입력창
    ├── MessageBubble.vue          # 개별 메시지 버블 (user/assistant/tool/system)
    ├── WelcomeMessage.vue         # 빈 대화 환영 메시지 + 빠른 시작 칩
    ├── TypingIndicator.vue        # 에이전트 처리 중 로딩 인디케이터
    └── HumanApproval.vue          # 도구 호출 승인/거부/수정 카드
```

## 아키텍처

### 전체 흐름

```
┌─────────────────────────────────────────────────────┐
│  App.vue                                            │
│  ┌──────────┐  ┌──────────────────────────────────┐ │
│  │ Sidebar  │  │ ChatView                         │ │
│  │          │  │  ┌────────────┐                  │ │
│  │ 스레드   │  │  │ ChatHeader │  LIVE / DEMO     │ │
│  │ 목록     │  │  ├────────────┤                  │ │
│  │          │  │  │ Welcome    │  (빈 상태일 때)  │ │
│  │          │  │  │ Message    │                   │ │
│  │          │  │  │ Bubble ×N  │  메시지 목록      │ │
│  │          │  │  │ Typing     │  (로딩 중)       │ │
│  │          │  │  │ HumanApp.  │  (승인 대기)     │ │
│  │          │  │  ├────────────┤                  │ │
│  │          │  │  │ ChatInput  │  메시지 입력      │ │
│  │          │  │  └────────────┘                  │ │
│  └──────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 컴포넌트 역할

**App.vue** — 루트 레이아웃. 서버 헬스체크(`/ok`)로 연결 상태를 판별하고, 스레드 생성/선택 상태를 관리한다. 서버 미연결 시 로컬 mock 스레드를 생성한다.

**Sidebar.vue** — 스레드 목록 표시, 새 대화 생성 버튼, 사이드바 접기/펼치기. `new-thread`, `select-thread`, `toggle` 이벤트를 emit한다.

**ChatView.vue** — 채팅 화면의 조합 레이어. `useChat`과 `useDemoMode` composable을 연결하고, 하위 컴포넌트들을 배치한다.

**ChatHeader.vue** — 상단 헤더. `threadId`를 표시하고, 서버 연결 상태에 따라 `LIVE` 또는 `DEMO` 배지를 보여준다.

**WelcomeMessage.vue** — 메시지가 없을 때 노출되는 환영 화면. 빠른 시작 칩 버튼 클릭 시 `send` 이벤트를 emit한다.

**MessageBubble.vue** — 개별 메시지 렌더링. `role`(user/assistant/tool/system)에 따라 다른 스타일을 적용하고, `marked`로 마크다운을 HTML로 변환한다. tool_calls가 있으면 호출 정보를 함께 표시한다.

**TypingIndicator.vue** — `isLoading` 상태일 때 표시되는 애니메이션 인디케이터.

**HumanApproval.vue** — `pendingApproval`이 있을 때 표시. 도구 이름·파라미터를 보여주고, 사용자가 승인(`approve`), 거부(`reject`, 사유 입력), 수정(`edit`, JSON 파라미터 편집) 중 하나를 선택할 수 있다.

**ChatInput.vue** — 하단 텍스트 입력. Enter로 전송, Shift+Enter로 줄바꿈. 승인 대기 중이거나 로딩 중이면 비활성화된다.

### Composables

**useChat.js** — 채팅의 핵심 상태와 로직을 캡슐화한다.

| 상태 | 설명 |
|------|------|
| `messages` | 전체 메시지 배열 (`role`, `content`, `timestamp`, ...) |
| `isLoading` | 에이전트 응답 대기 중 여부 |
| `pendingApproval` | 승인 대기 중인 도구 호출 정보 (`{ toolCalls }`) |
| `streamingContent` | SSE 스트리밍 중 누적 텍스트 |
| `scrollContainer` | 스크롤 영역 template ref |

| 함수 | 설명 |
|------|------|
| `sendMessage(text, simulateResponse)` | 사용자 메시지 추가 후, 서버 연결이면 `sendToServer`, 아니면 `simulateResponse` 호출 |
| `handleApprove(simulateToolResult)` | 도구 실행 승인. 서버면 `client.approveToolCall`, 아니면 `simulateToolResult` |
| `handleReject(reason)` | 도구 실행 거부. 서버면 `client.rejectToolCall` → `resumeRun` |
| `handleEdit(toolCallId, newArgs, simulateToolResult)` | 파라미터 수정 후 실행 |

서버 통신 시 `handleStreamEvent`가 SSE 이벤트를 파싱하여 메시지를 `messages`에 추가한다.
AI 메시지에 `tool_calls`가 포함되면 `pendingApproval`을 설정하여 HumanApproval 카드를 활성화한다.

**useDemoMode.js** — 서버 미연결 시의 시뮬레이션 로직.

| 함수 | 설명 |
|------|------|
| `simulateResponse(text)` | LOT ID가 포함된 메시지면 공정 이력 조회 → 이상 감지 → 도구 호출 시뮬레이션. 아니면 일반 안내 응답 |
| `simulateToolResult()` | 패턴 검사 결과 시뮬레이션 (CD 편차, Overlay 등) |

### API 클라이언트 (`langgraph.js`)

`LangGraphClient` 클래스가 LangGraph 서버의 REST API와 SSE 스트리밍을 처리한다.

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `createThread()` | `POST /threads` | 새 대화 스레드 생성 |
| `getThreadState(id)` | `GET /threads/:id/state` | 스레드 상태 조회 |
| `updateThreadState(id, values)` | `POST /threads/:id/state` | 스레드 상태 업데이트 |
| `streamRun(id, input, callbacks)` | `POST /threads/:id/runs/stream` | SSE 스트리밍 실행 |
| `approveToolCall(id, callbacks)` | (resumeRun 위임) | `command: { resume: true }`로 실행 재개 |
| `rejectToolCall(id, reason)` | (updateThreadState 위임) | reject ToolMessage 전송 |
| `editToolCall(id, toolCallId, newArgs)` | (getState → updateState) | tool_calls 파라미터 수정 |
| `healthCheck()` | `GET /ok` | 서버 연결 확인 |

### Human-in-the-Loop 플로우

```
사용자 메시지 전송
        │
        ▼
LangGraph 서버 스트리밍 실행
        │
        ▼
AI가 tool_calls 포함 응답 반환
        │
        ▼
pendingApproval 설정 → HumanApproval 카드 표시
        │
        ├── [승인] → approveToolCall → resume: true → 도구 실행 → 결과 스트리밍
        │
        ├── [거부] → rejectToolCall → ToolMessage("REJECTED: ...") → resumeRun
        │
        └── [수정] → editToolCall(파라미터 변경) → approveToolCall → 도구 실행
```

### 데모 모드 플로우

서버 미연결 시 `isConnected === false`로 판별되며, 모든 메시지 전송·승인·수정이 로컬 시뮬레이션으로 대체된다.

- `LOT-XXXX` 패턴 입력 → 공정 이력 조회 시뮬레이션 → 이상 감지 → 도구 호출 승인 요청
- 일반 텍스트 입력 → 랜덤 안내 응답
- 도구 승인/수정 → 패턴 검사 결과 시뮬레이션

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `VITE_LANGGRAPH_API_URL` | `''` (Vite proxy 사용) | LangGraph 서버 URL. 빈 값이면 같은 호스트의 프록시 경로 사용 |
