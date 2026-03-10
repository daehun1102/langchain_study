# Long-Term Polling Resume + Chat Block + Email Notify Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** (1) 세션 복원 시 장기 이력 PENDING 폴링 자동 재개, (2) PENDING 중 채팅 입력 차단, (3) 분석 완료 시 이메일 알림

**Architecture:**
- Frontend `useDefectChat.js` 단일 파일에 `longTermTaskId` state 추가 + `checkAndHandleBgStatus` 공통 함수 추출로 즉시 체크(C)와 인터벌(A) 재사용.
- `loadSession()` 진입 시 항상 `pollTimer` clear로 세션 간 격리 보장.
- 이메일: Frontend → `notifyEmail` 포함 → AI 서버 `long_term_node` → `_run_long_term_analysis` → `complete_bg_task` 후 `aiosmtplib` SMTP 발송.

**Tech Stack:** Vue 3 Composition API (`computed`), localStorage, setInterval / Python `aiosmtplib`, FastAPI Pydantic, pydantic-settings

---

### Task 1: `longTermTaskId` state 추가 및 `runAgents`에서 저장

**Files:**
- Modify: `frontend/src/composables/useDefectChat.js`

**Step 1: `longTermTaskId` ref 추가**

`useDefectChat.js` L24 `const pollTimer = ref(null)` 바로 아래:

```js
const pollTimer = ref(null)
const longTermTaskId = ref(null)
```

**Step 2: `runAgents()` 내 taskId 저장**

L211 현재:
```js
if (data.longTermTaskId) {
  pollBgStatus(data.longTermTaskId)
```

변경 후:
```js
if (data.longTermTaskId) {
  longTermTaskId.value = data.longTermTaskId
  pollBgStatus(data.longTermTaskId)
```

**Step 3: Commit**

```bash
git add frontend/src/composables/useDefectChat.js
git commit -m "feat: add longTermTaskId state and store on runAgents"
```

---

### Task 2: `saveCurrentSession()`에 `longTermTaskId` 포함

**Files:**
- Modify: `frontend/src/composables/useDefectChat.js:95-106`

**Step 1: record 객체에 필드 추가**

현재 L104-105 (`longTermStatus` 바로 위):
```js
      enabledAgents: { ...enabledAgents },
      longTermStatus: longTermStatus.value,
```

변경 후:
```js
      enabledAgents: { ...enabledAgents },
      longTermTaskId: longTermTaskId.value,
      longTermStatus: longTermStatus.value,
```

**Step 2: localStorage 저장 확인**

분석 실행 후 콘솔:
```js
JSON.parse(localStorage.getItem('defect_sessions'))[0].longTermTaskId
// → "3e7f8c2a-..." UUID 확인
```

**Step 3: Commit**

```bash
git add frontend/src/composables/useDefectChat.js
git commit -m "feat: persist longTermTaskId in localStorage session"
```

---

### Task 3: `checkAndHandleBgStatus()` 공통 처리 함수 추출

`pollBgStatus()` 내부 로직 전체를 분리해 즉시 체크와 인터벌이 동일 코드를 공유.

**Files:**
- Modify: `frontend/src/composables/useDefectChat.js:243-271`

**Step 1: `checkAndHandleBgStatus` 함수를 `pollBgStatus` 바로 위에 추가**

```js
async function checkAndHandleBgStatus(taskId) {
  const data = await getBgStatus(taskId)
  longTermStatus.value = data.status

  if (data.status === 'COMPLETED' || data.status === 'FAILED') {
    if (pollTimer.value) { clearInterval(pollTimer.value); pollTimer.value = null }
    longTermResult.value = data.resultText

    if (data.status === 'COMPLETED') {
      const response = await callAgent({
        sessionId: sessionId.value,
        action: 'resume_long_term',
        longTermResult: data.resultText || '',
      })
      const r = { suspectRows: [], analysis: data.resultText || '' }
      agentResults['long_term'] = r
      _updateMessage('long_term', 'done', r)
      finalActionPlan.value = response.finalActionPlan || ''
    } else {
      _updateMessage('long_term', 'error', null)
    }
    saveCurrentSession()
  }
}
```

**Step 2: `pollBgStatus()`를 위임 구조로 교체**

기존 `pollBgStatus` 함수 전체를 아래로 교체:

```js
function pollBgStatus(taskId) {
  pollTimer.value = setInterval(async () => {
    try {
      await checkAndHandleBgStatus(taskId)
    } catch (e) {
      clearInterval(pollTimer.value); pollTimer.value = null
    }
  }, 3000)
}
```

**Step 3: Commit**

```bash
git add frontend/src/composables/useDefectChat.js
git commit -m "refactor: extract checkAndHandleBgStatus for reuse"
```

---

### Task 4: `resumePollBgStatus()` 신규 함수 추가

세션 복원 시 즉시 1회 체크(C) 후 여전히 PENDING이면 인터벌 시작(A). loading 카드도 복원.

**Files:**
- Modify: `frontend/src/composables/useDefectChat.js` — `checkAndHandleBgStatus` 바로 아래

**Step 1: `resumePollBgStatus` 함수 추가**

```js
async function resumePollBgStatus(taskId) {
  // 메시지 카드 없으면 loading 카드 복원
  const hasCard = chatMessages.value.some(m => m.agentKey === 'long_term')
  if (!hasCard) {
    chatMessages.value.push({ id: uuidv4(), agentKey: 'long_term', status: 'loading', result: null })
  }
  // 즉시 1회 체크 — 이미 완료됐을 수 있음
  try {
    await checkAndHandleBgStatus(taskId)
  } catch (_) {}
  // 아직 PENDING이면 인터벌 시작
  if (longTermStatus.value === 'PENDING') {
    pollBgStatus(taskId)
  }
}
```

**Step 2: Commit**

```bash
git add frontend/src/composables/useDefectChat.js
git commit -m "feat: add resumePollBgStatus for session restore"
```

---

### Task 5: `loadSession()` 수정 — taskId 복원 + 세션 격리 + 폴링 재개

**Files:**
- Modify: `frontend/src/composables/useDefectChat.js:124-136`

**Step 1: `loadSession` 전체 교체**

현재:
```js
function loadSession(session) {
  activeSessionId.value = session.id
  sessionId.value = session.id
  form.productId = session.productId
  form.defectDescription = session.defectDescription
  selectedHypothesis.value = session.hypothesis
  chatMessages.value = session.chatMessages || []
  Object.assign(agentResults, session.agentResults)
  if (session.enabledAgents) Object.assign(enabledAgents, session.enabledAgents)
  longTermStatus.value = session.longTermStatus || 'PENDING'
  longTermResult.value = session.longTermResult || null
  step.value = 'result'
}
```

변경 후:
```js
function loadSession(session) {
  // 다른 세션으로 전환 시 기존 폴링 즉시 중단 (세션 간 격리 핵심)
  if (pollTimer.value) { clearInterval(pollTimer.value); pollTimer.value = null }

  activeSessionId.value = session.id
  sessionId.value = session.id
  form.productId = session.productId
  form.defectDescription = session.defectDescription
  selectedHypothesis.value = session.hypothesis
  chatMessages.value = session.chatMessages || []
  Object.assign(agentResults, session.agentResults)
  if (session.enabledAgents) Object.assign(enabledAgents, session.enabledAgents)
  longTermTaskId.value = session.longTermTaskId || null
  longTermStatus.value = session.longTermStatus || 'PENDING'
  longTermResult.value = session.longTermResult || null
  step.value = 'result'

  // PENDING + taskId 있으면 즉시 체크 후 필요 시 폴링 재개
  if (longTermTaskId.value && longTermStatus.value === 'PENDING') {
    resumePollBgStatus(longTermTaskId.value)
  }
}
```

**Step 2: 세션 격리 동작 확인**

1. 세션 A (long_term PENDING) 로드 → loading 카드 표시, 폴링 시작
2. 세션 B 로드 → 콘솔에서 A 폴링 중단 확인 (`pollTimer === null`)
3. 세션 A 다시 로드 → 폴링 재개, B의 `sessionId`로 resume이 호출되지 않는지 확인

**Step 3: Commit**

```bash
git add frontend/src/composables/useDefectChat.js
git commit -m "feat: resume long_term polling on session load with session isolation"
```

---

### Task 6: `newAnalysis()`에 `longTermTaskId` 초기화

**Files:**
- Modify: `frontend/src/composables/useDefectChat.js:139-155`

**Step 1: `longTermTaskId` 초기화 추가**

현재 L140-141:
```js
function newAnalysis() {
  if (pollTimer.value) { clearInterval(pollTimer.value); pollTimer.value = null }
  sessionId.value = uuidv4()
```

변경 후:
```js
function newAnalysis() {
  if (pollTimer.value) { clearInterval(pollTimer.value); pollTimer.value = null }
  longTermTaskId.value = null
  sessionId.value = uuidv4()
```

**Step 2: Commit**

```bash
git add frontend/src/composables/useDefectChat.js
git commit -m "fix: reset longTermTaskId on new analysis"
```

---

### Task 7: PENDING 중 채팅 입력 차단 — `isChatBlocked` + App.vue 적용

**Files:**
- Modify: `frontend/src/composables/useDefectChat.js`
- Modify: `frontend/src/App.vue`

**Step 1: `computed` import 추가**

`useDefectChat.js` L2:
```js
import { ref, reactive, watch } from 'vue'
```
변경 후:
```js
import { ref, reactive, watch, computed } from 'vue'
```

**Step 2: `isChatBlocked` computed 추가**

`longTermTaskId` 선언 바로 아래:
```js
const longTermTaskId = ref(null)
const isChatBlocked = computed(
  () => enabledAgents.long_term && longTermStatus.value === 'PENDING'
)
```

**Step 3: return에 `isChatBlocked` 노출**

`useDefectChat.js` return 객체 `longTermStatus` 옆:
```js
longTermStatus, longTermResult, finalActionPlan,
isChatBlocked,
```

**Step 4: `App.vue` — `isChatBlocked` destructure**

`App.vue` script setup:
```js
const {
  step, loading, error, form, hypotheses, selectedHypothesis,
  chatMessages,
  sessions, activeSessionId,
  enabledAgents,
  isChatBlocked,
  startAnalysis, selectHypothesis, runAgents, toggleAgent,
  newAnalysis, loadSession, deleteSession,
  userInput, sendUserMessage,
} = useDefectChat()
```

**Step 5: `App.vue` — 채팅 입력 영역 교체**

`App.vue` `<div class="chat-input-bar">` 전체를 아래로 교체:

```html
<div class="chat-input-bar">
  <div v-if="isChatBlocked" class="chat-blocked-notice">
    ⏳ 장기 이력 분석 완료 후 채팅이 가능합니다
  </div>
  <template v-else>
    <textarea
      v-model="userInput"
      class="chat-input"
      placeholder="결과에 대해 추가 질문을 입력하세요… (Enter로 전송)"
      rows="1"
      @keydown.enter.exact.prevent="sendUserMessage"
      @input="autoResize"
      ref="chatInputEl"
    ></textarea>
    <button
      class="chat-send-btn"
      :disabled="!userInput.trim() || loading"
      @click="sendUserMessage"
      title="전송"
    >
      <svg viewBox="0 0 16 16" fill="none" width="15" height="15">
        <path d="M14 8L2 2l3 6-3 6 12-6z" fill="currentColor"/>
      </svg>
    </button>
  </template>
</div>
```

**Step 6: `App.vue` — `.chat-blocked-notice` 스타일 추가**

`<style scoped>` 블록 하단:
```css
.chat-blocked-notice {
  flex: 1;
  text-align: center;
  color: #6b7280;
  font-size: 0.82rem;
  padding: 10px 0;
  font-style: italic;
}
```

**Step 7: 동작 확인**

1. 장기 이력 ON으로 에이전트 실행
2. PENDING 중 채팅 입력 영역이 안내 문구로 교체되는지 확인
3. 폴링 COMPLETED 후 채팅 입력창 복원 확인

**Step 8: Commit**

```bash
git add frontend/src/composables/useDefectChat.js frontend/src/App.vue
git commit -m "feat: block chat input while long_term is PENDING"
```

---

### Task 8: 이메일 설정 — Frontend `userEmail` state + `runAgents`에 포함

**Files:**
- Modify: `frontend/src/composables/useDefectChat.js`

**Step 1: `userEmail` state 추가 (localStorage 연동)**

`useDefectChat.js` `const userInput = ref('')` 바로 위:
```js
// 알림 이메일 (localStorage 영구 저장)
const userEmail = ref(localStorage.getItem('user_email') || '')
watch(userEmail, v => {
  try { localStorage.setItem('user_email', v || '') } catch (_) {}
})
```

**Step 2: `runAgents()` — `notifyEmail` 포함**

`callAgent` 호출부 (L195-200):
```js
const data = await callAgent({
  sessionId: sessionId.value,
  action: 'select_hypothesis',
  selectedHypothesis: selectedHypothesis.value,
  enabledAgents: enabledKeys,
  notifyEmail: userEmail.value || null,
})
```

**Step 3: return에 `userEmail` 노출**

```js
userInput, sendUserMessage,
userEmail,
```

**Step 4: Commit**

```bash
git add frontend/src/composables/useDefectChat.js
git commit -m "feat: add userEmail state with localStorage and pass to runAgents"
```

---

### Task 9: `App.vue` 헤더에 이메일 설정 UI 추가

**Files:**
- Modify: `frontend/src/App.vue`

**Step 1: `userEmail` destructure 추가**

script setup:
```js
const {
  ...
  isChatBlocked,
  userEmail,
  ...
} = useDefectChat()
```

**Step 2: 헤더에 이메일 입력 UI 추가**

`<header class="header">` 내부, `<span class="subtitle">` 바로 아래:
```html
<div class="email-setting">
  <label class="email-label">📧 알림 이메일</label>
  <input
    v-model="userEmail"
    type="email"
    class="email-input"
    placeholder="완료 알림 받을 이메일"
  />
</div>
```

**Step 3: 스타일 추가**

`<style scoped>` 하단:
```css
.email-setting {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}
.email-label {
  color: #6b7280;
  font-size: 0.78rem;
  white-space: nowrap;
}
.email-input {
  background: #1a1d27;
  border: 1px solid #2a2d3a;
  border-radius: 6px;
  padding: 5px 10px;
  color: #e0e0e0;
  font-size: 0.78rem;
  width: 200px;
  outline: none;
}
.email-input:focus { border-color: #00c8ff; }
.email-input::placeholder { color: #374151; }
```

**Step 4: 동작 확인**

1. 헤더 우측에 이메일 입력 필드 표시 확인
2. 입력 후 새로고침해도 유지되는지 확인 (localStorage)

**Step 5: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat: add email notification setting in header"
```

---

### Task 10: `server.py` — `AgentRequest`에 `notify_email` 추가

**Files:**
- Modify: `ai_server/server.py`

**Step 1: `AgentRequest`에 필드 추가**

`server.py` `user_message` 바로 아래:
```python
    user_message: Optional[str] = None
    notify_email: Optional[str] = None
```

**Step 2: `select_hypothesis` resume_value에 `notify_email` 포함**

`server.py` L142-147:
```python
if req.action == "select_hypothesis":
    resume_value = {
        "selected_hypothesis": req.selected_hypothesis,
        "enabled_agents": req.enabled_agents,
        "notify_email": req.notify_email,
    }
```

**Step 3: Commit**

```bash
git add ai_server/server.py
git commit -m "feat: add notify_email to AgentRequest and select_hypothesis resume"
```

---

### Task 11: `state.py` + `graph.py` — `notify_email` passthrough

**Files:**
- Modify: `ai_server/agents/state.py`
- Modify: `ai_server/agents/graph.py`
- Modify: `ai_server/server.py`

**Step 1: `SubAgentInput`에 `notify_email` 추가**

`state.py` L20-26:
```python
class SubAgentInput(TypedDict):
    company: str
    defect_description: str
    product_id: str
    selected_hypothesis: str
    session_id: str
    notify_email: Optional[str]
```

**Step 2: `DefectAnalysisState`에 `notify_email` 추가**

`enabled_agents` 바로 아래:
```python
    enabled_agents: list[str]
    notify_email: Optional[str]
```

**Step 3: `graph.py` `hypothesis_node` — `notify_email` passthrough**

`hypothesis_node` L83-86 반환부:
```python
    result: dict = {"hypotheses": hypotheses, "selected_hypothesis": selected}
    if enabled is not None:
        result["enabled_agents"] = enabled
    if isinstance(resume, dict) and resume.get("notify_email") is not None:
        result["notify_email"] = resume["notify_email"]
    return result
```

**Step 4: `server.py` `initial_state`에 `notify_email` 추가**

`initial_state` dict L122-138:
```python
        initial_state: DefectAnalysisState = {
            "company": req.company,
            "defect_description": req.defect_description,
            "product_id": req.product_id,
            "session_id": req.session_id,
            "enabled_agents": req.enabled_agents,
            "notify_email": None,
            "hypotheses": [],
            ...
        }
```

**Step 5: Commit**

```bash
git add ai_server/agents/state.py ai_server/agents/graph.py ai_server/server.py
git commit -m "feat: thread notify_email through state and hypothesis_node"
```

---

### Task 12: `config.py` + `.env.example` — SMTP 설정 추가

**Files:**
- Modify: `ai_server/config.py`
- Modify: `.env.example`

**Step 1: `Settings`에 SMTP 필드 추가**

`config.py` `model_name` 아래:
```python
    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # SMTP 이메일 알림
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
```

**Step 2: `.env.example`에 SMTP 항목 추가**

파일 하단:
```
# ── 이메일 알림 (장기 이력 완료 알림) ─────────────────────────────────────────
# Gmail 사용 시: 앱 비밀번호(App Password) 사용 필요
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com
```

**Step 3: Commit**

```bash
git add ai_server/config.py .env.example
git commit -m "feat: add SMTP settings to config"
```

---

### Task 13: `aiosmtplib` 설치 + `email_utils.py` 신규

**Files:**
- Modify: `ai_server/requirements.txt`
- Create: `ai_server/infra/email_utils.py`

**Step 1: `requirements.txt`에 추가**

`# Utils` 섹션:
```
aiosmtplib==3.0.2
```

**Step 2: venv에 설치**

```bash
cd ai_server && venv/Scripts/pip install aiosmtplib==3.0.2
```

**Step 3: `email_utils.py` 생성**

`ai_server/infra/email_utils.py` 전체:

```python
# ai_server/infra/email_utils.py
import logging
from email.mime.text import MIMEText

import aiosmtplib

from ai_server.config import get_settings

logger = logging.getLogger(__name__)


async def send_completion_email(to: str, product_id: str, result_text: str) -> None:
    """장기 이력 분석 완료 알림 이메일 발송.

    SMTP 설정이 없으면 조용히 skip.
    발송 실패 시 예외를 raise하지 않고 로그만 남김 (분석 결과에 영향 없음).
    """
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_user:
        logger.debug("SMTP 설정 없음 — 이메일 알림 skip")
        return

    subject = f"[장기 이력 분석 완료] 제품 {product_id}"
    body = (
        f"장기 이력 분석이 완료되었습니다.\n\n"
        f"제품 ID: {product_id}\n\n"
        f"── 분석 결과 ──\n{result_text}\n"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info("이메일 알림 발송 완료 → %s", to)
    except Exception as exc:
        logger.warning("이메일 발송 실패 (무시): %s", exc)
```

**Step 4: Commit**

```bash
git add ai_server/requirements.txt ai_server/infra/email_utils.py
git commit -m "feat: add aiosmtplib and email_utils for completion notification"
```

---

### Task 14: `long_term.py` — `notify_email` 수신 + 완료 후 이메일 발송

**Files:**
- Modify: `ai_server/agents/sub/long_term.py`

**Step 1: `send_completion_email` import 추가**

import 블록 하단:
```python
from ai_server.infra.email_utils import send_completion_email
```

**Step 2: `long_term_node` — `notify_email` 추출 및 전달**

```python
async def long_term_node(state: SubAgentInput) -> dict:
    task_id = str(uuid4())
    notify_email = state.get("notify_email")

    await insert_bg_task(task_id, state["session_id"])

    task = asyncio.create_task(
        _run_long_term_analysis(
            task_id,
            state["product_id"],
            state["selected_hypothesis"],
            notify_email,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {"long_term_task_id": task_id}
```

**Step 3: `_run_long_term_analysis` — `notify_email` 파라미터 추가 + 완료 후 발송**

```python
async def _run_long_term_analysis(
    task_id: str,
    product_id: str,
    hypothesis: str,
    notify_email: str | None = None,
):
    await asyncio.sleep(10)

    result_text = None
    try:
        result_text = await query_long_term_history(product_id)
        result_text += (
            f"\n\n[선택된 가설에 기반한 추가 분석]\n"
            f"{hypothesis}를 중심으로 6개월 추이를 분석한 결과, "
            f"재발 방지를 위한 공정 파라미터 조정이 필요합니다."
        )
    except Exception:
        pass

    if result_text is not None:
        await complete_bg_task(task_id, result_text)
        if notify_email:
            await send_completion_email(notify_email, product_id, result_text)
    else:
        await fail_bg_task(task_id)
```

**Step 4: Commit**

```bash
git add ai_server/agents/sub/long_term.py
git commit -m "feat: send email notification on long_term analysis completion"
```

---

### Task 15: 전체 통합 검증

**시나리오 1: 세션 복원 + 폴링 재개**

1. 장기 이력 ON으로 분석 시작
2. PENDING 중 다른 세션 클릭 → A 폴링 중단, B에서 채팅 가능 여부 확인
3. A 세션 다시 클릭 → loading 카드 복원, 즉시 1회 체크 시작
4. COMPLETED 후 done 카드 표시, 채팅 입력창 복원 확인

**시나리오 2: 페이지 새로고침 복원**

1. F5 새로고침 후 PENDING 세션 클릭
2. 폴링 재개 + 채팅 차단 안내 표시
3. 완료 후 자동 복원 확인

**시나리오 3: 세션 격리**

1. 세션 A (PENDING) 로드 → 폴링 시작
2. 세션 B 로드 → A의 `pollTimer`가 clear됐는지 확인
3. B에서 long_term이 없는 경우 채팅 즉시 가능한지 확인

**시나리오 4: 이메일 알림**

1. 헤더에 수신 이메일 입력
2. `.env`에 SMTP 설정 입력 후 AI 서버 재시작
3. 장기 이력 ON으로 분석 실행 → ~10초 후 이메일 수신 확인
4. SMTP 미설정 시 오류 없이 정상 동작하는지 확인 (로그에 "skip" 메시지)

**Final Commit**

```bash
git add .
git commit -m "feat: long_term polling resume, chat block, email notification complete"
```
