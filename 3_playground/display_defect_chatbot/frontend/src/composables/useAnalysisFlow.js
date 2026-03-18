// frontend/src/composables/useAnalysisFlow.js
import { ref, reactive, computed } from 'vue'
import { callAgent, getBgStatus, getSession, upsertSession } from '../api/defectApi.js'
import { uuidv4 } from './utils/uuid.js'

export const AGENT_CONFIG = [
  {
    key: 'process_history',
    label: '공정이력',
    icon: '⚙️',
    desc: '제품 제조 공정 단계별 이력을 조회하고 FAIL 항목 및 이상 공정을 분석합니다.',
    color: '#00c8ff',
    colDefs: [
      { field: 'process_step', headerName: '공정단계' },
      { field: 'result', headerName: '결과', cellClass: p => p.value === 'FAIL' ? 'cell-fail' : 'cell-pass' },
      { field: 'equipment_id', headerName: '설비ID' },
      { field: 'operator_id', headerName: '작업자' },
      { field: 'measured_at', headerName: '측정시간' },
    ],
  },
  {
    key: 'return_history',
    label: '반송이력',
    icon: '↩️',
    desc: '고객·공정 반송 이력을 조회하고 가설과 연관된 반복 불량 패턴을 분석합니다.',
    color: '#f59e0b',
    colDefs: [
      { field: 'return_reason', headerName: '반송 사유' },
      { field: 'severity', headerName: '심각도', cellClass: p => p.value === 'HIGH' ? 'cell-fail' : p.value === 'LOW' ? 'cell-pass' : 'cell-warn' },
      { field: 'quantity', headerName: '수량' },
      { field: 'return_date', headerName: '반송일' },
    ],
  },
  {
    key: 'test_history',
    label: '테스트이력',
    icon: '🧪',
    desc: '전기·광학 테스트 결과를 조회하고 규격 초과 항목을 식별합니다.',
    color: '#10b981',
    colDefs: [
      { field: 'test_type', headerName: '테스트 유형' },
      { field: 'result', headerName: '결과', cellClass: p => p.value === 'FAIL' ? 'cell-fail' : 'cell-pass' },
      { field: 'measured_value', headerName: '측정값' },
      { field: 'spec_min', headerName: '최소규격' },
      { field: 'spec_max', headerName: '최대규격' },
      { field: 'tested_at', headerName: '측정시간' },
    ],
  },
  {
    key: 'long_term',
    label: '장기이력',
    icon: '📊',
    desc: '동일 모델 최근 6개월 불량 통계를 분석합니다. (백그라운드 실행)',
    color: '#a78bfa',
    colDefs: [],
  },
]

export function useAnalysisFlow(chat, email) {
  const sessionId = ref(uuidv4())
  const step = ref('input')
  const loading = ref(false)
  const error = ref(null)
  const pollTimer = ref(null)

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

  const longTermTaskId = ref(null)
  const longTermStatus = ref('PENDING')
  const longTermResult = ref(null)
  const finalActionPlan = ref('')

  const isChatBlocked = computed(
    () => enabledAgents.long_term && longTermStatus.value === 'PENDING'
  )

  // --- 분석 함수들 ---

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

  async function selectHypothesis(h) {
    selectedHypothesis.value = h.text
    AGENT_CONFIG.forEach(a => { enabledAgents[a.key] = false })
    h.recommended_agents.forEach(key => { enabledAgents[key] = true })
    step.value = 'agent_select'
  }

  async function goBackToHypotheses() {
    step.value = 'hypotheses'
  }

  async function runAgents({ clearMessages = true } = {}) {
    step.value = 'result'
    loading.value = true
    if (clearMessages) chat.chatMessages.value = []

    const enabledKeys = AGENT_CONFIG.map(a => a.key).filter(k => enabledAgents[k])
    enabledKeys.forEach(k => {
      agentLoading[k] = true
      chat.chatMessages.value.push({ id: uuidv4(), agentKey: k, status: 'loading', result: null })
    })

    try {
      const data = await callAgent({
        sessionId: sessionId.value,
        action: 'select_hypothesis',
        selectedHypothesis: selectedHypothesis.value,
        enabledAgents: enabledKeys,
        notifyEmail: email.userEmail.value || null,
      })

      const results = data.agentResults || {}
      for (const [key, val] of Object.entries(results)) {
        if (val) {
          const r = { suspectRows: val.suspect_rows || [], analysis: val.analysis || '' }
          agentResults[key] = r
          chat._updateMessage(key, 'done', r)
        }
      }

      if (data.longTermTaskId) {
        longTermTaskId.value = data.longTermTaskId
        pollBgStatus(data.longTermTaskId)
      } else {
        const finalResp = await callAgent({
          sessionId: sessionId.value,
          action: 'resume_long_term',
          longTermResult: '',
        })
        finalActionPlan.value = finalResp.finalActionPlan || ''
      }
    } catch (e) {
      error.value = e.message
      enabledKeys.forEach(k => chat._updateMessage(k, 'error', null))
    } finally {
      enabledKeys.forEach(k => { agentLoading[k] = false })
      loading.value = false
    }
  }

  function toggleAgent(key) {
    enabledAgents[key] = !enabledAgents[key]
  }

  // 사용자 채팅 메시지 전송 (sessionId, error는 클로저 접근)
  async function sendUserMessage() {
    const text = chat.userInput.value.trim()
    if (!text) return
    chat.userInput.value = ''
    chat.chatMessages.value.push({ id: uuidv4(), agentKey: 'user', status: 'user', userText: text })

    try {
      const data = await callAgent({
        sessionId: sessionId.value,
        action: 'chat',
        userMessage: text,
      })
      if (data.reply) {
        chat.chatMessages.value.push({
          id: uuidv4(), agentKey: 'assistant', status: 'done',
          result: { analysis: data.reply, suspectRows: [] },
        })
      }
    } catch (e) {
      error.value = e.message
    }
  }

  // --- 백그라운드 폴링 (내부 헬퍼) ---

  function pollBgStatus(taskId) {
    const capturedSessionId = sessionId.value  // 폴링 시작 시점의 세션 ID 스냅샷
    pollTimer.value = setInterval(async () => {
      try {
        await checkAndHandleBgStatus(taskId, capturedSessionId)
      } catch (e) {
        clearInterval(pollTimer.value); pollTimer.value = null
      }
    }, 3000)
  }

  async function checkAndHandleBgStatus(taskId, capturedSessionId) {
    const data = await getBgStatus(taskId)
    const isStillActive = sessionId.value === capturedSessionId

    if (isStillActive) longTermStatus.value = data.status

    if (data.status === 'COMPLETED' || data.status === 'FAILED') {
      if (pollTimer.value) { clearInterval(pollTimer.value); pollTimer.value = null }

      if (!isStillActive) {
        // 세션 전환 후 완료: UI 건드리지 않고 이전 세션 DB에만 조용히 저장
        await _saveStaleSessionResult(capturedSessionId, data)
        return
      }

      longTermResult.value = data.resultText

      if (data.status === 'COMPLETED') {
        const response = await callAgent({
          sessionId: sessionId.value,
          action: 'resume_long_term',
          longTermResult: data.resultText || '',
        })
        const r = { suspectRows: [], analysis: data.resultText || '' }
        agentResults['long_term'] = r
        chat._updateMessage('long_term', 'done', r)
        finalActionPlan.value = response.finalActionPlan || ''
      } else {
        chat._updateMessage('long_term', 'error', null)
      }
      // 폴링 완료 시 자동 저장 (root composable에서 주입된 콜백)
      await _saveCallback.value()
    }
  }

  // 세션 전환 후 백그라운드 작업이 완료됐을 때: UI 갱신 없이 DB에만 저장
  async function _saveStaleSessionResult(targetSessionId, bgData) {
    try {
      const session = await getSession(targetSessionId)
      let finalPlan = session.finalActionPlan || ''
      if (bgData.status === 'COMPLETED') {
        const response = await callAgent({
          sessionId: targetSessionId,
          action: 'resume_long_term',
          longTermResult: bgData.resultText || '',
        })
        finalPlan = response.finalActionPlan || ''
      }
      const updatedAgentResults = {
        ...(session.agentResults || {}),
        long_term: bgData.status === 'COMPLETED'
          ? { suspectRows: [], analysis: bgData.resultText || '' }
          : null,
      }
      await upsertSession(targetSessionId, {
        ...session,
        agentResults: updatedAgentResults,
        longTermStatus: bgData.status,
        longTermResult: bgData.resultText || null,
        finalActionPlan: finalPlan,
      })
    } catch (e) {
      console.warn('[_saveStaleSessionResult] 저장 실패:', e)
    }
  }

  // 폴링 완료 시 자동 저장을 위한 콜백 (root composable에서 주입)
  const _saveCallback = ref(async () => {})
  function _setSaveCallback(fn) { _saveCallback.value = fn }

  // 세션 복원 시 미완료 폴링 재개 (useSessionManager에서 호출)
  async function resumePollBgStatus(taskId) {
    // 세션 전환 경쟁 조건 방지: await 전 sessionId 스냅샷
    const capturedSessionId = sessionId.value

    const hasCard = chat.chatMessages.value.some(m => m.agentKey === 'long_term')
    if (!hasCard) {
      chat.chatMessages.value.push({ id: uuidv4(), agentKey: 'long_term', status: 'loading', result: null })
    }

    try {
      await checkAndHandleBgStatus(taskId, capturedSessionId)
    } catch (e) {
      console.warn('[resumePollBgStatus] 즉시 체크 실패:', e)
    }

    // await 동안 세션이 바뀌었거나 이미 완료됐으면 인터벌 시작 안 함
    if (sessionId.value === capturedSessionId && longTermStatus.value === 'PENDING') {
      pollBgStatus(taskId)
    }
  }

  return {
    sessionId, step, loading, error,
    form, hypotheses, selectedHypothesis,
    enabledAgents, agentLoading, agentResults,
    longTermTaskId, longTermStatus, longTermResult,
    finalActionPlan, pollTimer,
    isChatBlocked,
    startAnalysis, selectHypothesis, goBackToHypotheses,
    runAgents, toggleAgent, sendUserMessage,
    resumePollBgStatus,
    _setSaveCallback,  // root composable에서 저장 콜백 주입용
  }
}
