// frontend/src/composables/useChatMessages.js
import { ref } from 'vue'

export function useChatMessages() {
  // { id, agentKey, status: 'loading'|'done'|'error'|'user', result: null|{ analysis, suspectRows }, userText? }
  const chatMessages = ref([])
  const userInput = ref('')

  // 내부용: useAnalysisFlow가 chat._updateMessage()로 호출한다.
  // App.vue에서 직접 사용하지 않는다.
  function _updateMessage(agentKey, status, result) {
    const idx = chatMessages.value.findLastIndex(m => m.agentKey === agentKey)
    if (idx >= 0) {
      chatMessages.value[idx] = { ...chatMessages.value[idx], status, result }
    }
  }

  return { chatMessages, userInput, _updateMessage }
}
