import { ref, nextTick, watch } from 'vue'
import { client } from '../api/langgraph.js'

export function useChat(props) {
  const messages = ref([])
  const isLoading = ref(false)
  const pendingApproval = ref(null)
  const scrollContainer = ref(null)
  const streamingContent = ref('')

  // 스크롤 맨 아래로
  function scrollToBottom() {
    nextTick(() => {
      const el = scrollContainer.value
      if (el) el.scrollTop = el.scrollHeight
    })
  }

  watch(messages, scrollToBottom, { deep: true })
  watch(streamingContent, scrollToBottom)

  // ─── 메시지 전송 ──────────────────────────────────────────

  async function sendMessage(text, simulateResponse) {
    messages.value.push({
      role: 'user',
      content: text,
      timestamp: Date.now(),
    })

    isLoading.value = true
    streamingContent.value = ''

    if (props.isConnected) {
      await sendToServer(text)
    } else {
      await simulateResponse(text)
    }
  }

  // ─── 서버 연결 모드 ────────────────────────────────────────

  function makeStreamCallbacks() {
    return {
      onEvent: handleStreamEvent,
      onError: (err) => {
        messages.value.push({
          role: 'system',
          content: `오류가 발생했습니다: ${err.message}`,
          timestamp: Date.now(),
        })
        isLoading.value = false
      },
      onComplete: () => {
        if (streamingContent.value) {
          messages.value.push({
            role: 'assistant',
            content: streamingContent.value,
            timestamp: Date.now(),
          })
          streamingContent.value = ''
        }
        isLoading.value = false
      },
    }
  }

  async function sendToServer(text) {
    try {
      await client.streamRun(
        props.threadId,
        { messages: [{ role: 'user', content: text }] },
        makeStreamCallbacks()
      )
    } catch (err) {
      messages.value.push({
        role: 'system',
        content: `연결 오류: ${err.message}`,
        timestamp: Date.now(),
      })
      isLoading.value = false
    }
  }

  function handleStreamEvent({ event, data }) {
    if (!data) return

    for (const [nodeName, nodeOutput] of Object.entries(data)) {
      if (!nodeOutput) continue

      const msgs = nodeOutput.messages || []
      for (const msg of msgs) {
        if (msg.type === 'ai' || msg.role === 'assistant') {
          if (msg.tool_calls?.length) {
            messages.value.push({
              role: 'assistant',
              content: msg.content || '',
              toolCalls: msg.tool_calls,
              agentName: nodeName,
              timestamp: Date.now(),
            })
            pendingApproval.value = {
              toolCalls: msg.tool_calls,
            }
            isLoading.value = false
          } else if (msg.content) {
            messages.value.push({
              role: 'assistant',
              content: msg.content,
              agentName: nodeName,
              timestamp: Date.now(),
            })
          }
        } else if (msg.type === 'tool' || msg.role === 'tool') {
          messages.value.push({
            role: 'tool',
            content: msg.content,
            toolName: msg.name,
            timestamp: Date.now(),
          })
        }
      }
    }
  }

  // ─── Human-in-the-loop 핸들러 ──────────────────────────────

  async function handleApprove(simulateToolResult) {
    pendingApproval.value = null
    isLoading.value = true

    messages.value.push({
      role: 'system',
      content: '도구 실행을 승인했습니다.',
      timestamp: Date.now(),
    })

    if (props.isConnected) {
      await client.approveToolCall(props.threadId, makeStreamCallbacks())
    } else {
      await simulateToolResult()
    }
  }

  async function handleReject(reason) {
    pendingApproval.value = null
    isLoading.value = true

    messages.value.push({
      role: 'system',
      content: `도구 실행을 거부했습니다: ${reason}`,
      timestamp: Date.now(),
    })

    if (props.isConnected) {
      await client.rejectToolCall(props.threadId, reason)
      await client.resumeRun(props.threadId, {
        ...makeStreamCallbacks(),
        command: { resume: reason },
      })
    } else {
      isLoading.value = false
    }
  }

  async function handleEdit(toolCallId, newArgs, simulateToolResult) {
    pendingApproval.value = null
    isLoading.value = true

    messages.value.push({
      role: 'system',
      content: `도구 파라미터를 수정 후 실행합니다.`,
      timestamp: Date.now(),
    })

    if (props.isConnected) {
      await client.editToolCall(props.threadId, toolCallId, newArgs)
      await client.approveToolCall(props.threadId, makeStreamCallbacks())
    } else {
      await simulateToolResult()
    }
  }

  return {
    messages,
    isLoading,
    pendingApproval,
    scrollContainer,
    streamingContent,
    sendMessage,
    handleApprove,
    handleReject,
    handleEdit,
  }
}
