// display_defect_chatbot/frontend/src/composables/useDefectChat.js
import { ref, reactive } from 'vue'
import { analyzeDefect, investigateDefect, getBgStatus } from '../api/defectApi.js'

function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16)
  })
}

export function useDefectChat() {
  const sessionId = ref(uuidv4())
  const step = ref('input')  // input | hypotheses | investigating | result
  const loading = ref(false)
  const error = ref(null)

  const form = reactive({ company: '', defectDescription: '', productId: '' })
  const hypotheses = ref([])
  const selectedHypothesis = ref('')
  const result = reactive({
    actionPlan: '',
    processHistory: [],
    returnHistory: [],
    testResults: [],
    longTermTaskId: null,
    longTermStatus: 'PENDING',
    longTermResult: null,
  })

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

  async function investigate(hypothesis) {
    selectedHypothesis.value = hypothesis
    loading.value = true
    step.value = 'investigating'
    try {
      const data = await investigateDefect({
        sessionId: sessionId.value,
        company: form.company,
        defectDescription: form.defectDescription,
        productId: form.productId,
        selectedHypothesis: hypothesis,
      })
      result.actionPlan = data.actionPlan
      result.processHistory = data.processHistory || []
      result.returnHistory = data.returnHistory || []
      result.testResults = data.testResults || []
      result.longTermTaskId = data.longTermTaskId
      step.value = 'result'

      if (data.longTermTaskId) {
        pollBgStatus(data.longTermTaskId)
      }
    } catch (e) {
      error.value = e.message
      step.value = 'hypotheses'
    } finally {
      loading.value = false
    }
  }

  function pollBgStatus(taskId) {
    const timer = setInterval(async () => {
      const data = await getBgStatus(taskId)
      result.longTermStatus = data.status
      if (data.status === 'COMPLETED' || data.status === 'FAILED') {
        result.longTermResult = data.resultText
        clearInterval(timer)
      }
    }, 3000)
  }

  function reset() {
    sessionId.value = uuidv4()
    step.value = 'input'
    hypotheses.value = []
    selectedHypothesis.value = ''
    Object.assign(result, {
      actionPlan: '', processHistory: [], returnHistory: [], testResults: [],
      longTermTaskId: null, longTermStatus: 'PENDING', longTermResult: null,
    })
  }

  return { sessionId, step, loading, error, form, hypotheses, selectedHypothesis, result, analyze, investigate, reset }
}
