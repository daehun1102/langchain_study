// frontend/src/composables/useSessionManager.js
import { ref, onMounted } from 'vue'
import {
  fetchSessions as apiFetchSessions,
  getSession as apiGetSession,
  upsertSession as apiUpsertSession,
  deleteSession as apiDeleteSession,
  updateSessionTitle as apiUpdateSessionTitle,
} from '../api/defectApi.js'
import { AGENT_CONFIG } from './useAnalysisFlow.js'
import { uuidv4 } from './utils/uuid.js'

export function useSessionManager(analysis, chat) {
  const sessions = ref([])
  const activeSessionId = ref(null)

  // 앱 마운트 시 DB에서 세션 목록 초기 로드
  onMounted(async () => {
    try {
      sessions.value = await apiFetchSessions()
    } catch (_) {
      sessions.value = []
    }
  })

  async function saveCurrentSession() {
    const id = analysis.sessionId.value
    const existing = sessions.value.find(s => s.id === id)

    const isPlaceholder = !existing?.title || existing.title === '새 분석'
    const title = isPlaceholder
      ? (() => {
          const base = analysis.selectedHypothesis.value
            ? analysis.selectedHypothesis.value.slice(0, 30)
            : analysis.form.defectDescription.slice(0, 30)
          return `${analysis.form.productId || 'Unknown'} — ${base || '새 분석'}`
        })()
      : existing.title

    const payload = {
      title,
      productId: analysis.form.productId,
      defectDescription: analysis.form.defectDescription,
      hypothesis: analysis.selectedHypothesis.value,
      agentResults: JSON.parse(JSON.stringify(analysis.agentResults)),
      chatMessages: JSON.parse(JSON.stringify(chat.chatMessages.value)),
      enabledAgents: { ...analysis.enabledAgents },
      longTermTaskId: analysis.longTermTaskId.value,
      longTermStatus: analysis.longTermStatus.value,
      longTermResult: analysis.longTermResult.value,
      finalActionPlan: analysis.finalActionPlan.value,
      step: analysis.step.value,
      hypotheses: JSON.parse(JSON.stringify(analysis.hypotheses.value)),
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
      analysis.error.value = `세션 저장 실패: ${e.message}`
    }
  }

  async function loadSession(targetId) {
    // 폴링 중이면 중단
    if (analysis.pollTimer.value) {
      clearInterval(analysis.pollTimer.value)
      analysis.pollTimer.value = null
    }

    try {
      const session = await apiGetSession(targetId)

      activeSessionId.value = session.id
      analysis.sessionId.value = session.id
      analysis.form.productId = session.productId || ''
      analysis.form.defectDescription = session.defectDescription || ''
      analysis.selectedHypothesis.value = session.hypothesis || ''
      chat.chatMessages.value = Array.isArray(session.chatMessages) ? session.chatMessages : []
      chat.userInput.value = ''

      AGENT_CONFIG.forEach(a => {
        analysis.agentResults[a.key] = session.agentResults?.[a.key] ?? null
        analysis.agentLoading[a.key] = false
        analysis.enabledAgents[a.key] = session.enabledAgents?.[a.key] ?? (a.key !== 'long_term')
      })

      analysis.longTermTaskId.value = session.longTermTaskId || null
      analysis.longTermStatus.value = session.longTermStatus || 'PENDING'
      analysis.longTermResult.value = session.longTermResult || null
      analysis.finalActionPlan.value = session.finalActionPlan || ''
      analysis.hypotheses.value = Array.isArray(session.hypotheses) ? session.hypotheses : []
      analysis.loading.value = false
      analysis.error.value = null

      // step 복원: DB 값 우선, 없으면 결과 유무로 판단 (구버전 세션 호환)
      const hasResults = chat.chatMessages.value.length > 0 ||
        AGENT_CONFIG.some(a => analysis.agentResults[a.key] !== null)
      analysis.step.value = session.step || (hasResults ? 'result' : 'input')

      // 미완료 장기이력이면 폴링 재개
      if (analysis.longTermTaskId.value && analysis.longTermStatus.value === 'PENDING') {
        analysis.resumePollBgStatus(analysis.longTermTaskId.value)
      }
    } catch (e) {
      if (e.status === 404) {
        sessions.value = sessions.value.filter(s => s.id !== targetId)
      }
      analysis.error.value = `세션 로드 실패: ${e.message}`
    }
  }

  async function deleteSession(id) {
    try {
      await apiDeleteSession(id)
      sessions.value = sessions.value.filter(s => s.id !== id)
      if (activeSessionId.value === id) {
        activeSessionId.value = null
      }
    } catch (e) {
      analysis.error.value = `세션 삭제 실패: ${e.message}`
    }
  }

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

  async function newAnalysis() {
    if (analysis.pollTimer.value) { clearInterval(analysis.pollTimer.value); analysis.pollTimer.value = null }

    analysis.longTermTaskId.value = null
    analysis.sessionId.value = uuidv4()
    activeSessionId.value = null
    analysis.step.value = 'input'
    analysis.hypotheses.value = []
    analysis.selectedHypothesis.value = ''
    analysis.loading.value = false
    analysis.error.value = null
    analysis.longTermStatus.value = 'PENDING'
    analysis.longTermResult.value = null
    chat.chatMessages.value = []
    analysis.form.productId = ''
    analysis.form.defectDescription = ''
    AGENT_CONFIG.forEach(a => {
      analysis.enabledAgents[a.key] = a.key !== 'long_term'
      analysis.agentLoading[a.key] = false
      analysis.agentResults[a.key] = null
    })

    await saveCurrentSession()
  }

  return {
    sessions, activeSessionId,
    saveCurrentSession, loadSession,
    deleteSession, updateSessionTitle, newAnalysis,
  }
}
