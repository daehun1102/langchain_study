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
