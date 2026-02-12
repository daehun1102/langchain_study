import { ref, watch, nextTick } from 'vue'
import { sendChat } from '../api/ncsApi.js'

export function useChat() {
  const messages = ref([])
  const isLoading = ref(false)
  const scrollContainer = ref(null)
  const activeFilter = ref({ mainCategory: null, subCategory: null })

  function setFilter(mainCategory, subCategory) {
    activeFilter.value = { mainCategory, subCategory }
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

    // Add user message
    messages.value.push({
      role: 'user',
      content: text,
      timestamp: Date.now(),
    })
    scrollToBottom()

    isLoading.value = true

    try {
      const result = await sendChat(
        text,
        activeFilter.value.mainCategory,
        activeFilter.value.subCategory,
      )

      // Add assistant response with sources
      messages.value.push({
        role: 'assistant',
        content: result.answer,
        sources: result.sources || [],
        filter: result.filter,
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
    activeFilter,
    setFilter,
    sendMessage,
  }
}
