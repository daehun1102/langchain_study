// display_defect_chatbot/frontend/src/composables/useDefectChat.js
import { ref, reactive, watch, computed, onMounted } from 'vue'
import {
  callAgent,
  getBgStatus,
  fetchSessions as apiFetchSessions,
  getSession as apiGetSession,
  upsertSession as apiUpsertSession,
  deleteSession as apiDeleteSession,
  updateSessionTitle as apiUpdateSessionTitle,
} from '../api/defectApi.js'

function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16)
  })
}

export const AGENT_CONFIG = [
  { key: 'process_history', label: '공정이력', icon: '⚙️', desc: '제품 제조 공정 단계별 이력을 조회하고 FAIL 항목 및 이상 공정을 분석합니다.' },
  { key: 'return_history',  label: '반송이력', icon: '↩️', desc: '고객·공정 반송 이력을 조회하고 가설과 연관된 반복 불량 패턴을 분석합니다.' },
  { key: 'test_history',    label: '테스트이력', icon: '🧪', desc: '전기·광학 테스트 결과를 조회하고 규격 초과 항목을 식별합니다.' },
  { key: 'long_term',       label: '장기이력',  icon: '📊', desc: '동일 모델 최근 6개월 불량 통계를 분석합니다. (백그라운드 실행)' },
]

export function useDefectChat() {
  const sessionId = ref(uuidv4())
  const step = ref('input')
  const loading = ref(false)
  const error = ref(null)
  const pollTimer = ref(null)
  const longTermTaskId = ref(null)

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
  const isChatBlocked = computed(
    () => enabledAgents.long_term && longTermStatus.value === 'PENDING'
  )
  const finalActionPlan = ref('')

  // --- 신규: 채팅 메시지 스트림 ---
  // { id, agentKey, status: 'loading'|'done'|'error'|'user', result: null|{ analysis, suspectRows }, userText?: string }
  const chatMessages = ref([])

  // 알림 이메일 (localStorage 영구 저장)
  const userEmail = ref(localStorage.getItem('user_email') || '')
  watch(userEmail, v => {
    try { localStorage.setItem('user_email', v || '') } catch (_) {}
  })

  // 사용자 입력
  const userInput = ref('')

  async function sendUserMessage() {
    const text = userInput.value.trim()
    if (!text) return
    userInput.value = ''
    chatMessages.value.push({ id: uuidv4(), agentKey: 'user', status: 'user', userText: text })

    try {
      const data = await callAgent({
        sessionId: sessionId.value,
        action: 'chat',
        userMessage: text,
      })
      if (data.reply) {
        chatMessages.value.push({ id: uuidv4(), agentKey: 'assistant', status: 'done', result: { analysis: data.reply, suspectRows: [] } })
      }
    } catch (e) {
      error.value = e.message
    }
  }

  // --- 분석 이력 세션 ---
  const sessions = ref([])
  const activeSessionId = ref(null)

  // 앱 마운트 시 DB에서 세션 목록 로드
  onMounted(async () => {
    try {
      sessions.value = await apiFetchSessions()
    } catch (_) {
      sessions.value = []
    }
  })

  // --- 세션 저장 (에이전트 완료 후 자동 호출) ---
  async function saveCurrentSession() {
    const id = sessionId.value
    const existing = sessions.value.find(s => s.id === id)
    const title = existing?.title
      || (() => {
           const base = selectedHypothesis.value
             ? selectedHypothesis.value.slice(0, 30)
             : form.defectDescription.slice(0, 30)
           return `${form.productId || 'Unknown'} — ${base || '새 분석'}`
         })()

    const payload = {
      title,
      productId: form.productId,
      defectDescription: form.defectDescription,
      hypothesis: selectedHypothesis.value,
      agentResults: JSON.parse(JSON.stringify(agentResults)),
      chatMessages: JSON.parse(JSON.stringify(chatMessages.value)),
      enabledAgents: { ...enabledAgents },
      longTermTaskId: longTermTaskId.value,
      longTermStatus: longTermStatus.value,
      longTermResult: longTermResult.value,
      finalActionPlan: finalActionPlan.value,
    }

    try {
      const summary = await apiUpsertSession(id, payload)
      const idx = sessions.value.findIndex(s => s.id === id)
      if (idx >= 0) {
        sessions.value[idx] = summary
      } else {
        sessions.value.unshift(summary)
      }
      activeSessionId.value = id
    } catch (e) {
      error.value = `세션 저장 실패: ${e.message}`
    }
  }

  // --- 세션 삭제 ---
  async function deleteSession(id) {
    try {
      await apiDeleteSession(id)
      sessions.value = sessions.value.filter(s => s.id !== id)
      if (activeSessionId.value === id) {
        activeSessionId.value = null
      }
    } catch (e) {
      error.value = `세션 삭제 실패: ${e.message}`
    }
  }

  // --- 세션 불러오기 (LeftPanel 클릭 시 ID로 호출) ---
  async function loadSession(targetId) {
    if (pollTimer.value) { clearInterval(pollTimer.value); pollTimer.value = null }

    try {
      const session = await apiGetSession(targetId)

      activeSessionId.value = session.id
      sessionId.value = session.id
      form.productId = session.productId
      form.defectDescription = session.defectDescription
      selectedHypothesis.value = session.hypothesis
      chatMessages.value = session.chatMessages || []
      // 이전 세션 결과 잔존 방지: 전체 초기화 후 복원
      AGENT_CONFIG.forEach(a => { agentResults[a.key] = null })
      Object.assign(agentResults, session.agentResults)
      if (session.enabledAgents) Object.assign(enabledAgents, session.enabledAgents)
      longTermTaskId.value = session.longTermTaskId || null
      longTermStatus.value = session.longTermStatus || 'PENDING'
      longTermResult.value = session.longTermResult || null
      finalActionPlan.value = session.finalActionPlan || ''
      step.value = 'result'

      if (longTermTaskId.value && longTermStatus.value === 'PENDING') {
        resumePollBgStatus(longTermTaskId.value)
      }
    } catch (e) {
      if (e.status === 404) {
        sessions.value = sessions.value.filter(s => s.id !== targetId)
      }
      error.value = `세션 로드 실패: ${e.message}`
    }
  }

  // --- 세션 제목 수정 ---
  async function updateSessionTitle(id, newTitle) {
    try {
      const summary = await apiUpdateSessionTitle(id, newTitle)
      const idx = sessions.value.findIndex(s => s.id === id)
      if (idx >= 0) {
        sessions.value[idx] = { ...sessions.value[idx], title: summary.title }
      }
    } catch (e) {
      if (e.status === 404) {
        sessions.value = sessions.value.filter(s => s.id !== id)
      }
      throw e  // LeftPanel이 원래 title로 복원할 수 있도록 re-throw
    }
  }

  // --- 새 분석 시작 ---
  function newAnalysis() {
    if (pollTimer.value) { clearInterval(pollTimer.value); pollTimer.value = null }
    longTermTaskId.value = null   // ← add this line
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

  async function startAnalysis() {
    loading.value = true
    error.value = null
    try {
      const data = await callAgent({
        sessionId: sessionId.value,
        action: 'start',
        company: form.company,
        defectDescription: form.defectDescription,
        productId: form.productId,
        enabledAgents: AGENT_CONFIG.map(a => a.key).filter(k => enabledAgents[k]),
      })
      hypotheses.value = data.hypotheses || []
      step.value = 'hypotheses'
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  function selectHypothesis(h) {
    selectedHypothesis.value = h.text

    // 가설 선택 시 전체 초기화 후 추천 에이전트만 ON (이후 수동 변경 가능)
    AGENT_CONFIG.forEach(a => { enabledAgents[a.key] = false })
    h.recommended_agents.forEach(key => { enabledAgents[key] = true })

    step.value = 'agent_select'
  }

  function goBackToHypotheses() {
    step.value = 'hypotheses'
  }

  async function runAgents() {
    step.value = 'result'
    loading.value = true
    chatMessages.value = []

    const enabledKeys = AGENT_CONFIG.map(a => a.key).filter(k => enabledAgents[k])
    enabledKeys.forEach(k => {
      agentLoading[k] = true
      chatMessages.value.push({ id: uuidv4(), agentKey: k, status: 'loading', result: null })
    })

    // 분석 시작 즉시 세션 카드 생성 (LeftPanel에 바로 표시)
    await saveCurrentSession()

    try {
      const data = await callAgent({
        sessionId: sessionId.value,
        action: 'select_hypothesis',
        selectedHypothesis: selectedHypothesis.value,
        enabledAgents: enabledKeys,
        notifyEmail: userEmail.value || null,
      })

      const results = data.agentResults || {}
      for (const [key, val] of Object.entries(results)) {
        if (val) {
          const r = { suspectRows: val.suspect_rows || [], analysis: val.analysis || '' }
          agentResults[key] = r
          _updateMessage(key, 'done', r)
        }
      }

      if (data.longTermTaskId) {
        longTermTaskId.value = data.longTermTaskId
        pollBgStatus(data.longTermTaskId)
      } else {
        // 장기이력 미실행: 즉시 resume → final synthesis 트리거
        const finalResp = await callAgent({
          sessionId: sessionId.value,
          action: 'resume_long_term',
          longTermResult: '',
        })
        finalActionPlan.value = finalResp.finalActionPlan || ''
      }
    } catch (e) {
      error.value = e.message
      enabledKeys.forEach(k => _updateMessage(k, 'error', null))
    } finally {
      enabledKeys.forEach(k => { agentLoading[k] = false })
      loading.value = false
      saveCurrentSession()
    }
  }

  function toggleAgent(key) {
    enabledAgents[key] = !enabledAgents[key]
  }

  function _updateMessage(agentKey, status, result) {
    const idx = chatMessages.value.findLastIndex(m => m.agentKey === agentKey)
    if (idx >= 0) {
      chatMessages.value[idx] = { ...chatMessages.value[idx], status, result }
    }
  }

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

  async function resumePollBgStatus(taskId) {
    const capturedSessionId = sessionId.value  // 세션 전환 감지용 스냅샷

    // 메시지 카드 없으면 loading 카드 복원
    const hasCard = chatMessages.value.some(m => m.agentKey === 'long_term')
    if (!hasCard) {
      chatMessages.value.push({ id: uuidv4(), agentKey: 'long_term', status: 'loading', result: null })
    }
    // 즉시 1회 체크 — 이미 완료됐을 수 있음
    try {
      await checkAndHandleBgStatus(taskId)
    } catch (e) {
      console.warn('[resumePollBgStatus] 즉시 체크 실패:', e)
    }
    // await 동안 세션이 바뀌었거나 이미 완료됐으면 인터벌 시작 안 함
    if (sessionId.value === capturedSessionId && longTermStatus.value === 'PENDING') {
      pollBgStatus(taskId)
    }
  }

  function pollBgStatus(taskId) {
    pollTimer.value = setInterval(async () => {
      try {
        await checkAndHandleBgStatus(taskId)
      } catch (e) {
        clearInterval(pollTimer.value); pollTimer.value = null
      }
    }, 3000)
  }

  // reset은 newAnalysis로 대체 (하위 호환)
  const reset = newAnalysis

  return {
    sessionId, step, loading, error,
    form, hypotheses, selectedHypothesis,
    enabledAgents, agentLoading, agentResults,
    longTermStatus, longTermResult, finalActionPlan,
    isChatBlocked,
    chatMessages,
    userInput, sendUserMessage,
    userEmail,
    sessions, activeSessionId,
    startAnalysis, selectHypothesis, goBackToHypotheses, runAgents, toggleAgent,
    saveCurrentSession, deleteSession, loadSession, updateSessionTitle, newAnalysis, reset,
  }
}
