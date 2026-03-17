// src/composables/useChatbotFlow.js
// useDefectChat()을 래핑하여 챗봇 흐름을 메시지 주입 방식으로 관리한다.
import { ref } from 'vue'
import { useDefectChat, AGENT_CONFIG } from './useDefectChat.js'
import { uuidv4 } from './utils/uuid.js'

export function useChatbotFlow() {
  const base = useDefectChat()

  // 현재 입력 모드 — ChatInputBar의 mode prop에 바인딩
  const inputMode = ref({
    type: 'text',
    placeholder: '제품ID와 불량 내용을 입력하세요…',
  })

  // --- 시스템 메시지 헬퍼 ---
  function pushSystem(text) {
    base.chatMessages.value.push({
      id: uuidv4(),
      agentKey: 'system',
      status: 'system',
      text,
    })
  }

  // --- long_term 폴링 완료 시 final_plan 버블 주입 ---
  // 반드시 setup 동기 코드에서 실행 — useSessionManager의 onMounted(resumePollBgStatus)보다 먼저 실행된다.
  base._setSaveCallback(async () => {
    await base.saveCurrentSession()
    if (base.finalActionPlan.value) {
      const alreadyPushed = base.chatMessages.value.some(m => m.status === 'final_plan')
      if (!alreadyPushed) {
        base.chatMessages.value.push({
          id: uuidv4(),
          agentKey: 'system',
          status: 'final_plan',
          text: base.finalActionPlan.value,
        })
      }
    }
  })

  // --- 1단계: 사용자 불량 내용 제출 ---
  async function submitDefect(text) {
    base.form.defectDescription = text
    pushSystem('가설을 생성하고 있습니다…')

    await base.startAnalysis()

    if (base.error.value) {
      pushSystem(`오류가 발생했습니다: ${base.error.value}`)
      // inputMode를 text 유지 → 사용자가 재시도 가능
      return
    }

    base.chatMessages.value.push({
      id: uuidv4(),
      agentKey: 'system',
      status: 'hypothesis_select',
      hypotheses: [...base.hypotheses.value],  // 스냅샷
      done: false,
    })
    inputMode.value = { type: 'single', options: base.hypotheses.value }
  }

  // --- 2단계: 가설 선택 ---
  async function onSelectHypothesis(h) {
    // hypothesis_select 버블 비활성화
    const msg = base.chatMessages.value.findLast(m => m.status === 'hypothesis_select')
    if (msg) msg.done = true

    // 사용자 선택을 user 버블로 표시
    base.chatMessages.value.push({
      id: uuidv4(),
      agentKey: 'user',
      status: 'user',
      userText: h.text,
    })

    await base.selectHypothesis(h)

    // selectHypothesis 완료 후 enabledAgents 스냅샷
    base.chatMessages.value.push({
      id: uuidv4(),
      agentKey: 'system',
      status: 'agent_select',
      agents: AGENT_CONFIG,
      enabledAgents: { ...base.enabledAgents },  // 스냅샷
      done: false,
    })
    inputMode.value = {
      type: 'multi',
      options: AGENT_CONFIG,
      enabledAgents: { ...base.enabledAgents },
    }
  }

  // --- 3단계: 에이전트 실행 ---
  async function onRunAgents(selectedKeys) {
    // agent_select 버블 비활성화
    const msg = base.chatMessages.value.findLast(m => m.status === 'agent_select')
    if (msg) msg.done = true

    // 선택된 에이전트를 user 버블로 표시
    const labels = AGENT_CONFIG
      .filter(a => selectedKeys.includes(a.key))
      .map(a => `${a.icon} ${a.label}`)
      .join(', ')
    base.chatMessages.value.push({
      id: uuidv4(),
      agentKey: 'user',
      status: 'user',
      userText: `선택한 에이전트: ${labels}`,
    })

    // enabledAgents 반영
    AGENT_CONFIG.forEach(a => { base.enabledAgents[a.key] = selectedKeys.includes(a.key) })

    // clearMessages: false — 챗봇 대화 이력 보존
    await base.runAgents({ clearMessages: false })

    if (base.error.value) {
      pushSystem(`분석 중 오류가 발생했습니다: ${base.error.value}`)
    }

    // long_term 없는 경우 즉시 finalActionPlan 사용 가능
    if (base.finalActionPlan.value) {
      const alreadyPushed = base.chatMessages.value.some(m => m.status === 'final_plan')
      if (!alreadyPushed) {
        base.chatMessages.value.push({
          id: uuidv4(),
          agentKey: 'system',
          status: 'final_plan',
          text: base.finalActionPlan.value,
        })
      }
    }

    inputMode.value = { type: 'text', placeholder: '추가 질문을 입력하세요…' }
  }

  // --- sendUserMessage 래퍼 ---
  // useAnalysisFlow의 sendUserMessage는 chat.userInput.value를 직접 읽는다.
  async function sendChatMessage(text) {
    base.userInput.value = text
    await base.sendUserMessage()
  }

  // --- handleSubmit: ChatbotApp의 @submit 단일 핸들러 ---
  async function handleSubmit(value) {
    const type = inputMode.value.type
    if (type === 'single') {
      await onSelectHypothesis(value)
    } else if (type === 'multi') {
      await onRunAgents(value)
    } else {
      // type='text'
      if (base.step.value === 'input') {
        await submitDefect(value)
      } else {
        await sendChatMessage(value)
      }
    }
  }

  return {
    ...base,
    inputMode,
    handleSubmit,
    onSelectHypothesis,
    onRunAgents,
  }
}
