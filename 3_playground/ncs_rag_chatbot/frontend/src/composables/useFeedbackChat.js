import { ref, watch, nextTick } from 'vue'
import { sendFeedbackChat } from '../api/ncsApi.js'

export function useFeedbackChat(version = 'v1') {
  const messages = ref([])
  const isLoading = ref(false)
  const scrollContainer = ref(null)
  const threadId = ref(crypto.randomUUID())

  function resetThread() {
    threadId.value = crypto.randomUUID()
    messages.value = []
  }

  function scrollToBottom() {
    nextTick(() => {
      if (scrollContainer.value) {
        scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
      }
    })
  }

  watch(messages, scrollToBottom, { deep: true })

  async function sendMessage(text) {
    if (!text.trim() || isLoading.value) return

    messages.value.push({
      role: 'user',
      content: text,
      timestamp: Date.now(),
    })
    scrollToBottom()

    isLoading.value = true

    try {
      const result = await sendFeedbackChat(text, threadId.value, version)

      messages.value.push({
        role: 'assistant',
        content: result.answer,
        sources: [],          // sources 표시 안 함 (RAG는 동작, UI만 숨김)
        timestamp: Date.now(),
      })
    } catch (err) {
      messages.value.push({
        role: 'system',
        content: `서버 연결 오류: ${err.message}. 서버가 실행 중인지 확인해주세요.`,
        timestamp: Date.now(),
      })
    } finally {
      isLoading.value = false
      scrollToBottom()
    }
  }

  return {
    messages,
    isLoading,
    scrollContainer,
    threadId,
    resetThread,
    sendMessage,
  }
}
