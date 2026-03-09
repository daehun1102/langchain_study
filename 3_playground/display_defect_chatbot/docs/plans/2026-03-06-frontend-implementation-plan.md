# Frontend Dashboard + Chatbot UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split-layout UI — 왼쪽 분석 이력 패널(localStorage CRD) + 오른쪽 하이브리드 챗봇(기존 단계 흐름 유지 + 에이전트 결과 말풍선 스트림).

**Architecture:** App.vue를 flex row 레이아웃으로 전환. useDefectChat.js에 sessions/chatMessages 상태 추가. 신규 LeftPanel.vue와 ChatStream.vue 생성. AgentResultPanel.vue는 제거(ChatStream이 대체).

**Tech Stack:** Vue 3 Composition API, Vite, AG Grid Community v33, localStorage

---

## Task 1: useDefectChat.js — sessions + chatMessages 상태 추가

**Files:**
- Modify: `frontend/src/composables/useDefectChat.js`

**Step 1: sessions, chatMessages 상태 및 localStorage 동기화 추가**

`useDefectChat.js` 전체를 아래로 교체:

```js
// display_defect_chatbot/frontend/src/composables/useDefectChat.js
import { ref, reactive, watch } from 'vue'
import { analyzeDefect, investigateDefect, getBgStatus } from '../api/defectApi.js'

function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16)
  })
}

export const AGENT_CONFIG = [
  { key: 'process_history', label: '공정이력', icon: '⚙️', desc: '제품 제조 공정 단계별 이력을 조회하고 FAIL 항목 및 이상 공정을 분석합니다.' },
  { key: 'return_history',  label: '반송이력', icon: '↩️', desc: '고객·공정 반송 이력을 조회하고 가설과 연관된 반복 불량 패턴을 분석합니다.' },
  { key: 'test_result',     label: '테스트결과', icon: '🧪', desc: '전기·광학 테스트 결과를 조회하고 규격 초과 항목을 식별합니다.' },
  { key: 'long_term',       label: '장기이력',  icon: '📊', desc: '동일 모델 최근 6개월 불량 통계를 분석합니다. (백그라운드 실행)' },
]

export function useDefectChat() {
  const sessionId = ref(uuidv4())
  const step = ref('input')
  const loading = ref(false)
  const error = ref(null)

  const form = reactive({
    company: 'SDC',
    defectDescription: '화면 좌측 상단 픽셀 10개가 완전히 꺼져 있음 (Dead Pixel)',
    productId: 'LOT-A001',
  })

  const hypotheses = ref([])
  const selectedHypothesis = ref('')

  const enabledAgents = reactive(
    Object.fromEntries(AGENT_CONFIG.map(a => [a.key, a.key !== 'long_term']))
  )

  const agentLoading = reactive(Object.fromEntries(AGENT_CONFIG.map(a => [a.key, false])))
  const agentResults = reactive(Object.fromEntries(AGENT_CONFIG.map(a => [a.key, null])))

  const longTermStatus = ref('PENDING')
  const longTermResult = ref(null)

  // --- 신규: 채팅 메시지 스트림 ---
  // { id, agentKey, status: 'loading'|'done'|'error', result: null|{ analysis, suspectRows } }
  const chatMessages = ref([])

  // --- 신규: 분석 이력 세션 ---
  // { id, productId, defectDescription, hypothesis, timestamp, agentResults, chatMessages }
  const sessions = ref([])
  const activeSessionId = ref(null)

  // localStorage 초기 로드
  try {
    const saved = localStorage.getItem('defect_sessions')
    if (saved) sessions.value = JSON.parse(saved)
  } catch (_) {}

  // sessions 변경 시 localStorage 동기화
  watch(sessions, (val) => {
    try {
      localStorage.setItem('defect_sessions', JSON.stringify(val))
    } catch (_) {}
  }, { deep: true })

  // --- 세션 저장 (에이전트 완료 후 자동 호출) ---
  function saveCurrentSession() {
    const id = sessionId.value
    const existing = sessions.value.findIndex(s => s.id === id)
    const record = {
      id,
      productId: form.productId,
      defectDescription: form.defectDescription,
      hypothesis: selectedHypothesis.value,
      timestamp: new Date().toISOString(),
      agentResults: JSON.parse(JSON.stringify(agentResults)),
      chatMessages: JSON.parse(JSON.stringify(chatMessages.value)),
      enabledAgents: { ...enabledAgents },
    }
    if (existing >= 0) {
      sessions.value[existing] = record
    } else {
      sessions.value.unshift(record)
    }
    activeSessionId.value = id
  }

  // --- 세션 삭제 ---
  function deleteSession(id) {
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (activeSessionId.value === id) {
      activeSessionId.value = null
    }
  }

  // --- 세션 불러오기 (왼쪽 패널 클릭 시) ---
  function loadSession(session) {
    activeSessionId.value = session.id
    sessionId.value = session.id
    form.productId = session.productId
    form.defectDescription = session.defectDescription
    selectedHypothesis.value = session.hypothesis
    chatMessages.value = session.chatMessages || []
    Object.assign(agentResults, session.agentResults)
    step.value = 'result'
  }

  // --- 새 분석 시작 ---
  function newAnalysis() {
    sessionId.value = uuidv4()
    activeSessionId.value = null
    step.value = 'input'
    hypotheses.value = []
    selectedHypothesis.value = ''
    loading.value = false
    longTermStatus.value = 'PENDING'
    longTermResult.value = null
    chatMessages.value = []
    AGENT_CONFIG.forEach(a => {
      enabledAgents[a.key] = a.key !== 'long_term'
      agentLoading[a.key] = false
      agentResults[a.key] = null
    })
  }

  async function analyze() {
    loading.value = true
    error.value = null
    try {
      const data = await analyzeDefect({
        sessionId: sessionId.value,
        company: form.company,
        defectDescription: form.defectDescription,
      })
      hypotheses.value = data.hypotheses
      step.value = 'hypotheses'
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  function selectHypothesis(hypothesis) {
    selectedHypothesis.value = hypothesis
    step.value = 'agent_select'
  }

  function toggleAgent(key) {
    enabledAgents[key] = !enabledAgents[key]
  }

  async function runAllEnabled() {
    error.value = null
    step.value = 'result'
    loading.value = true
    chatMessages.value = []

    const enabledKeys = AGENT_CONFIG.map(a => a.key).filter(k => enabledAgents[k])

    // 실행할 에이전트마다 로딩 말풍선 즉시 추가
    enabledKeys.forEach(k => {
      agentLoading[k] = true
      chatMessages.value.push({ id: uuidv4(), agentKey: k, status: 'loading', result: null })
    })

    try {
      const data = await investigateDefect({
        sessionId: sessionId.value,
        company: form.company,
        defectDescription: form.defectDescription,
        productId: form.productId,
        selectedHypothesis: selectedHypothesis.value,
        enabledAgents: enabledKeys,
      })

      if (data.processHistory) {
        const r = { suspectRows: data.processHistory.suspectRows || [], analysis: data.processHistory.analysis || '' }
        agentResults['process_history'] = r
        _updateMessage('process_history', 'done', r)
      }
      if (data.returnHistory) {
        const r = { suspectRows: data.returnHistory.suspectRows || [], analysis: data.returnHistory.analysis || '' }
        agentResults['return_history'] = r
        _updateMessage('return_history', 'done', r)
      }
      if (data.testResults) {
        const r = { suspectRows: data.testResults.suspectRows || [], analysis: data.testResults.analysis || '' }
        agentResults['test_result'] = r
        _updateMessage('test_result', 'done', r)
      }
      if (data.longTermTaskId) pollBgStatus(data.longTermTaskId)

    } catch (e) {
      error.value = e.message
      enabledKeys.forEach(k => _updateMessage(k, 'error', null))
    } finally {
      enabledKeys.forEach(k => { agentLoading[k] = false })
      loading.value = false
      saveCurrentSession()
    }
  }

  function _updateMessage(agentKey, status, result) {
    const idx = chatMessages.value.findLastIndex(m => m.agentKey === agentKey)
    if (idx >= 0) {
      chatMessages.value[idx] = { ...chatMessages.value[idx], status, result }
    }
  }

  function pollBgStatus(taskId) {
    const timer = setInterval(async () => {
      const data = await getBgStatus(taskId)
      longTermStatus.value = data.status
      if (data.status === 'COMPLETED' || data.status === 'FAILED') {
        longTermResult.value = data.resultText
        if (data.status === 'COMPLETED') {
          const r = { suspectRows: [], analysis: data.resultText || '' }
          agentResults['long_term'] = r
          _updateMessage('long_term', 'done', r)
        } else {
          _updateMessage('long_term', 'error', null)
        }
        clearInterval(timer)
        saveCurrentSession()
      }
    }, 3000)
  }

  // reset은 newAnalysis로 대체 (하위 호환)
  const reset = newAnalysis

  return {
    sessionId, step, loading, error,
    form, hypotheses, selectedHypothesis,
    enabledAgents, agentLoading, agentResults,
    longTermStatus, longTermResult,
    chatMessages,
    sessions, activeSessionId,
    analyze, selectHypothesis, toggleAgent, runAllEnabled,
    saveCurrentSession, deleteSession, loadSession, newAnalysis, reset,
  }
}
```

**Step 2: 개발 서버 실행 후 콘솔 에러 없는지 확인**

```bash
cd frontend && npm run dev
```

Expected: 브라우저에서 기존 UI 정상 동작, 콘솔 에러 없음

**Step 3: Commit**

```bash
git add frontend/src/composables/useDefectChat.js
git commit -m "feat(frontend): add sessions/chatMessages state with localStorage sync"
```

---

## Task 2: LeftPanel.vue 생성

**Files:**
- Create: `frontend/src/components/LeftPanel.vue`

**Step 1: 파일 생성**

```vue
<template>
  <aside class="left-panel">
    <div class="panel-header">
      <h2>분석 이력</h2>
      <button class="btn-new" @click="$emit('new-analysis')">+ 새 분석</button>
    </div>

    <div class="session-list">
      <p v-if="sessions.length === 0" class="empty-hint">분석 이력이 없습니다.</p>

      <div
        v-for="session in sessions"
        :key="session.id"
        class="session-card"
        :class="{ active: session.id === activeSessionId }"
        @click="$emit('load-session', session)"
      >
        <div class="card-top">
          <span class="product-id">{{ session.productId || '-' }}</span>
          <button class="btn-delete" @click.stop="$emit('delete-session', session.id)">🗑</button>
        </div>
        <p class="defect-desc">{{ truncate(session.defectDescription) }}</p>
        <div class="card-bottom">
          <span class="agent-icons">
            <span v-for="agent in ranAgents(session)" :key="agent.key">{{ agent.icon }}</span>
          </span>
          <span class="timestamp">{{ formatDate(session.timestamp) }}</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { AGENT_CONFIG } from '../composables/useDefectChat.js'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  activeSessionId: { type: String, default: null },
})
defineEmits(['new-analysis', 'load-session', 'delete-session'])

function truncate(str) {
  if (!str) return '-'
  return str.length > 32 ? str.slice(0, 32) + '...' : str
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function ranAgents(session) {
  return AGENT_CONFIG.filter(a => session.agentResults?.[a.key])
}
</script>

<style scoped>
.left-panel {
  width: 280px;
  min-width: 280px;
  background: #1a1d27;
  border-right: 1px solid #2a2d3a;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #2a2d3a;
}
.panel-header h2 { font-size: 0.95rem; color: #60a5fa; }

.btn-new {
  background: #1d4ed8;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 0.78rem;
  cursor: pointer;
}
.btn-new:hover { background: #2563eb; }

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-hint { color: #4b5563; font-size: 0.82rem; text-align: center; margin-top: 24px; }

.session-card {
  background: #0f1117;
  border: 1px solid #2a2d3a;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.session-card:hover { border-color: #374151; }
.session-card.active { border-color: #3b82f6; background: #0f1c35; }

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.product-id { font-size: 0.85rem; color: #93c5fd; font-weight: 600; }

.btn-delete {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  opacity: 0.5;
  padding: 0;
  line-height: 1;
}
.btn-delete:hover { opacity: 1; }

.defect-desc { font-size: 0.78rem; color: #6b7280; margin-bottom: 8px; line-height: 1.4; }

.card-bottom { display: flex; align-items: center; justify-content: space-between; }
.agent-icons { font-size: 0.9rem; letter-spacing: 2px; }
.timestamp { font-size: 0.72rem; color: #4b5563; }
</style>
```

**Step 2: 개발 서버에서 컴포넌트 import 에러 없는지 확인 (App.vue 연결 전)**

임시로 App.vue에 import만 추가해서 에러 없는지 확인.

**Step 3: Commit**

```bash
git add frontend/src/components/LeftPanel.vue
git commit -m "feat(frontend): add LeftPanel component with session CRD"
```

---

## Task 3: ChatStream.vue 생성

**Files:**
- Create: `frontend/src/components/ChatStream.vue`

**Step 1: 파일 생성**

```vue
<template>
  <div class="chat-stream" ref="streamEl">
    <div v-if="messages.length === 0" class="chat-empty">
      에이전트를 실행하면 분석 결과가 여기에 표시됩니다.
    </div>

    <div v-for="msg in messages" :key="msg.id" class="chat-bubble">
      <!-- 말풍선 헤더 -->
      <div class="bubble-header">
        <span class="agent-avatar">🤖</span>
        <span class="agent-label">{{ agentLabel(msg.agentKey) }}</span>
        <span v-if="msg.status === 'loading'" class="spinner-sm"></span>
        <span v-else-if="msg.status === 'done'" class="badge-done">완료</span>
        <span v-else-if="msg.status === 'error'" class="badge-error">오류</span>
      </div>

      <!-- 로딩 중 -->
      <div v-if="msg.status === 'loading'" class="bubble-body loading-body">
        분석 중...
      </div>

      <!-- 완료 -->
      <div v-else-if="msg.status === 'done' && msg.result" class="bubble-body">
        <div class="analysis-text">{{ msg.result.analysis }}</div>

        <template v-if="msg.result.suspectRows?.length">
          <div class="grid-label">의심 데이터</div>
          <AgGridVue
            class="ag-theme-quartz-dark grid-box"
            :rowData="msg.result.suspectRows"
            :columnDefs="getColDefs(msg.agentKey)"
            :defaultColDef="defaultColDef"
            domLayout="autoHeight"
          />
        </template>
        <p v-else class="no-data">의심 데이터 없음</p>
      </div>

      <!-- 오류 -->
      <div v-else-if="msg.status === 'error'" class="bubble-body error-body">
        분석 중 오류가 발생했습니다.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community'
import { AGENT_CONFIG } from '../composables/useDefectChat.js'

ModuleRegistry.registerModules([AllCommunityModule])

const props = defineProps({
  messages: { type: Array, default: () => [] },
})

const streamEl = ref(null)

// 새 메시지 추가 시 스크롤 하단으로
watch(() => props.messages.length, async () => {
  await nextTick()
  if (streamEl.value) streamEl.value.scrollTop = streamEl.value.scrollHeight
})

const defaultColDef = { resizable: true, sortable: true, filter: true, flex: 1, minWidth: 80 }

const COL_DEFS = {
  process_history: [
    { field: 'process_step', headerName: '공정단계' },
    { field: 'result', headerName: '결과', cellClass: p => p.value === 'FAIL' ? 'cell-fail' : 'cell-pass' },
    { field: 'equipment_id', headerName: '설비ID' },
    { field: 'operator_id', headerName: '작업자' },
    { field: 'measured_at', headerName: '측정시간' },
  ],
  return_history: [
    { field: 'return_reason', headerName: '반송 사유' },
    { field: 'severity', headerName: '심각도', cellClass: p => p.value === 'HIGH' ? 'cell-fail' : p.value === 'LOW' ? 'cell-pass' : 'cell-warn' },
    { field: 'quantity', headerName: '수량' },
    { field: 'return_date', headerName: '반송일' },
  ],
  test_result: [
    { field: 'test_type', headerName: '테스트 유형' },
    { field: 'result', headerName: '결과', cellClass: p => p.value === 'FAIL' ? 'cell-fail' : 'cell-pass' },
    { field: 'measured_value', headerName: '측정값' },
    { field: 'spec_min', headerName: '최소규격' },
    { field: 'spec_max', headerName: '최대규격' },
    { field: 'tested_at', headerName: '측정시간' },
  ],
}

function getColDefs(agentKey) { return COL_DEFS[agentKey] || [] }

function agentLabel(agentKey) {
  return AGENT_CONFIG.find(a => a.key === agentKey)?.label || agentKey
}
</script>

<style>
/* AG Grid 셀 색상 (전역) */
.cell-fail { color: #f87171 !important; font-weight: 600; }
.cell-pass { color: #4ade80 !important; }
.cell-warn { color: #fbbf24 !important; }
</style>

<style scoped>
.chat-stream {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-empty {
  color: #4b5563;
  font-size: 0.85rem;
  text-align: center;
  margin-top: 40px;
}

.chat-bubble {
  background: #1a1d27;
  border: 1px solid #2a2d3a;
  border-radius: 12px;
  overflow: hidden;
}

.bubble-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid #2a2d3a;
  background: #1e2130;
}
.agent-avatar { font-size: 1rem; }
.agent-label { font-size: 0.85rem; color: #93c5fd; font-weight: 600; flex: 1; }

.badge-done {
  font-size: 0.7rem; padding: 2px 8px; border-radius: 4px;
  background: #064e3b; color: #6ee7b7;
}
.badge-error {
  font-size: 0.7rem; padding: 2px 8px; border-radius: 4px;
  background: #7f1d1d; color: #fca5a5;
}

.bubble-body { padding: 14px; }

.loading-body { color: #6b7280; font-size: 0.85rem; font-style: italic; }
.error-body { color: #f87171; font-size: 0.85rem; }

.analysis-text {
  color: #d1d5db;
  font-size: 0.85rem;
  line-height: 1.7;
  margin-bottom: 12px;
  white-space: pre-wrap;
}

.grid-label { color: #6b7280; font-size: 0.75rem; margin-bottom: 6px; }
.grid-box { border-radius: 6px; overflow: hidden; font-size: 0.78rem; }
.no-data { color: #4b5563; font-size: 0.82rem; margin: 0; }

.spinner-sm {
  width: 12px; height: 12px;
  border: 2px solid #374151;
  border-top-color: #60a5fa;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
```

**Step 2: 개발 서버에서 에러 없는지 확인**

**Step 3: Commit**

```bash
git add frontend/src/components/ChatStream.vue
git commit -m "feat(frontend): add ChatStream component for agent results as chat bubbles"
```

---

## Task 4: App.vue — Split Layout으로 전체 재구성

**Files:**
- Modify: `frontend/src/App.vue`

**Step 1: App.vue 전체 교체**

```vue
<template>
  <div class="app">
    <!-- 헤더 -->
    <header class="header">
      <h1>🔬 Display Defect Analyzer</h1>
      <span class="subtitle">삼성 디스플레이 픽셀 불량 분석 AI</span>
    </header>

    <div class="body">
      <!-- 왼쪽: 분석 이력 패널 -->
      <LeftPanel
        :sessions="sessions"
        :activeSessionId="activeSessionId"
        @new-analysis="newAnalysis"
        @load-session="loadSession"
        @delete-session="deleteSession"
      />

      <!-- 오른쪽: 단계별 흐름 + ChatStream -->
      <main class="right-panel">
        <!-- 단계별 흐름 영역 (결과 단계가 아닐 때 또는 입력/가설/에이전트 선택 중) -->
        <div class="flow-area" :class="{ collapsed: step === 'result' }">
          <InputView
            v-if="step === 'input'"
            :form="form" :loading="loading" :error="error"
            @analyze="analyze"
          />
          <HypothesisSelector
            v-if="step === 'hypotheses'"
            :hypotheses="hypotheses" :loading="loading"
            @select="selectHypothesis"
          />
          <AgentSelector
            v-if="step === 'agent_select'"
            :hypothesis="selectedHypothesis"
            :enabledAgents="enabledAgents"
            :loading="loading"
            @toggle="toggleAgent"
            @run-all="runAllEnabled"
          />
        </div>

        <!-- result 단계: 가설 배지 + ChatStream -->
        <template v-if="step === 'result'">
          <div class="result-header">
            <div class="hypothesis-badge">선택된 가설: {{ selectedHypothesis }}</div>
            <button class="btn-reset" @click="newAnalysis">새 분석 시작</button>
          </div>
          <ChatStream :messages="chatMessages" />
        </template>
      </main>
    </div>
  </div>
</template>

<script setup>
import { useDefectChat } from './composables/useDefectChat.js'
import LeftPanel from './components/LeftPanel.vue'
import InputView from './components/InputView.vue'
import HypothesisSelector from './components/HypothesisSelector.vue'
import AgentSelector from './components/AgentSelector.vue'
import ChatStream from './components/ChatStream.vue'

const {
  step, loading, error, form, hypotheses, selectedHypothesis,
  enabledAgents, agentLoading, agentResults,
  longTermStatus, chatMessages,
  sessions, activeSessionId,
  analyze, selectHypothesis, toggleAgent, runAllEnabled,
  newAnalysis, loadSession, deleteSession,
} = useDefectChat()
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0f1117; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
</style>

<style scoped>
.app { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }

.header {
  background: #1a1d27;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 1px solid #2a2d3a;
  flex-shrink: 0;
}
.header h1 { font-size: 1.2rem; color: #60a5fa; }
.subtitle { color: #6b7280; font-size: 0.85rem; }

.body { display: flex; flex: 1; overflow: hidden; }

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.flow-area {
  padding: 24px;
  overflow-y: auto;
  flex-shrink: 0;
  max-height: 60vh;
}
.flow-area.collapsed { display: none; }

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #2a2d3a;
  flex-shrink: 0;
}
.hypothesis-badge {
  background: #1e3a5f;
  border: 1px solid #3b82f6;
  border-radius: 8px;
  padding: 8px 14px;
  color: #93c5fd;
  font-size: 0.85rem;
}
.btn-reset {
  background: #374151;
  color: #e0e0e0;
  border: none;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}
.btn-reset:hover { background: #4b5563; }
</style>
```

**Step 2: 개발 서버 실행 후 전체 레이아웃 동작 확인**

- 왼쪽 패널 표시 확인
- 기존 입력→가설→에이전트선택 흐름 정상 동작 확인
- "새 분석 시작" 버튼 동작 확인

**Step 3: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat(frontend): redesign App.vue with split dashboard layout"
```

---

## Task 5: 통합 검증 + AgentResultPanel 정리

**Files:**
- Check: 전체 흐름 end-to-end 동작
- Optional Delete: `frontend/src/components/AgentResultPanel.vue` (App.vue에서 더 이상 사용 안 함)

**Step 1: 전체 흐름 수동 테스트 체크리스트**

1. [ ] 개발 서버 시작: `cd frontend && npm run dev`
2. [ ] 불량 설명 입력 후 "원인 분석 시작" 클릭 → 가설 목록 표시
3. [ ] 가설 선택 → 에이전트 선택 화면 표시
4. [ ] 에이전트 실행 → ChatStream에 로딩 말풍선 즉시 표시
5. [ ] 결과 수신 → 말풍선이 결과 카드(분석 텍스트 + AG Grid)로 교체
6. [ ] 완료 후 왼쪽 패널에 세션 카드 자동 추가 확인
7. [ ] "새 분석 시작" → 초기화 확인
8. [ ] 브라우저 새로고침 후 왼쪽 패널에 이전 세션 복원 확인
9. [ ] 세션 카드 클릭 → 오른쪽에 해당 결과 복원 확인
10. [ ] 🗑 버튼으로 세션 삭제 확인

**Step 2: AgentResultPanel.vue 삭제**

App.vue에서 import 및 사용이 제거됐으므로 파일 삭제:

```bash
rm frontend/src/components/AgentResultPanel.vue
```

**Step 3: 최종 빌드 확인**

```bash
cd frontend && npm run build
```

Expected: `dist/` 폴더 생성, 빌드 에러 없음

**Step 4: Final Commit**

```bash
git add -A
git commit -m "feat(frontend): complete dashboard+chatbot UI redesign — remove AgentResultPanel"
```

---

## 완료 기준

- [ ] 좌우 split layout 정상 동작
- [ ] 분석 이력 세션 CRD (자동생성, 클릭복원, 삭제)
- [ ] localStorage 영속 (새로고침 후 복원)
- [ ] 에이전트 결과 말풍선 스트림 (로딩 → 완료 전환)
- [ ] AG Grid 테이블 ChatStream 내 정상 렌더링
- [ ] 빌드 에러 없음
