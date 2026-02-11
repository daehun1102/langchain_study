import { ref, nextTick, watch } from 'vue'
import { client } from '../api/langgraph.js'

export function useChat(props) {
  const messages = ref([])
  const isLoading = ref(false)
  const pendingApproval = ref(null)
  const scrollContainer = ref(null)
  const streamingContent = ref('')

  // localStorage에서 메시지 로드
  function loadMessages() {
    const key = `thread_messages_${props.threadId}`
    const saved = localStorage.getItem(key)
    if (saved) {
      try {
        messages.value = JSON.parse(saved)
      } catch {
        messages.value = []
      }
    } else {
      messages.value = []
    }
  }

  // localStorage에 메시지 저장
  function saveMessages() {
    const key = `thread_messages_${props.threadId}`
    localStorage.setItem(key, JSON.stringify(messages.value))
  }

  // 초기 로드
  loadMessages()

  // 스크롤 맨 아래로
  function scrollToBottom() {
    nextTick(() => {
      const el = scrollContainer.value
      if (el) el.scrollTop = el.scrollHeight
    })
  }

  watch(messages, () => {
    scrollToBottom()
    saveMessages()
  }, { deep: true })
  watch(streamingContent, scrollToBottom)

  // Thread 제목 생성
  function generateTitle(text) {
    const lotMatch = text.match(/LOT[-\s]?(\S+)/i)
    if (lotMatch) {
      return `LOT-${lotMatch[1]} 검사`
    }
    return text.length > 40 ? text.substring(0, 40) + '...' : text
  }

  // ─── 메시지 전송 ──────────────────────────────────────────

  async function sendMessage(text, simulateResponse) {
    const isFirstMessage = messages.value.length === 0

    messages.value.push({
      role: 'user',
      content: text,
      timestamp: Date.now(),
    })

    // 첫 메시지일 때 제목 업데이트 이벤트 발생
    if (isFirstMessage) {
      const title = generateTitle(text)
      window.dispatchEvent(new CustomEvent('thread-title-update', {
        detail: { threadId: props.threadId, title },
      }))
    }

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
      // StateGraph 입력: { user_request: "..." }
      await client.streamRun(
        props.threadId,
        { user_request: text },
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
      // ─── __interrupt__ 이벤트 감지 ───
      if (nodeName === '__interrupt__') {
        const interrupts = Array.isArray(nodeOutput) ? nodeOutput : [nodeOutput]
        const interruptValue = interrupts[0] || {}
        const args = interruptValue.args || {}
        pendingApproval.value = {
          action: interruptValue.action || 'router_decision_review',
          args,
          description: interruptValue.description || '',
          toolCalls: [{
            name: args.process ? `${args.process} 공정 검사` : 'router_decision_review',
            args,
            id: 'interrupt',
          }],
        }
        isLoading.value = false
        return
      }

      if (!nodeOutput || typeof nodeOutput !== 'object') continue

      // ─── StateGraph 노드 출력 처리 ───
      // classifier 노드: classification (표시하지 않음)
      if (nodeName === 'classifier') continue

      // chat 노드: final_answer
      if (nodeName === 'chat' && nodeOutput.final_answer) {
        messages.value.push({
          role: 'assistant',
          content: nodeOutput.final_answer,
          agentName: 'chat',
          timestamp: Date.now(),
        })
        continue
      }

      // history 노드: history_summary
      if (nodeOutput.history_summary) {
        messages.value.push({
          role: 'assistant',
          content: nodeOutput.history_summary,
          agentName: 'history',
          timestamp: Date.now(),
        })
      }

      // router_decision 노드: routing_decision
      if (nodeOutput.routing_decision) {
        const decision = nodeOutput.routing_decision
        messages.value.push({
          role: 'assistant',
          content: `공정 선택: **${decision.process}** — ${decision.reason || ''}`,
          agentName: 'router',
          timestamp: Date.now(),
        })
      }

      // process 노드: process_result
      if (nodeOutput.process_result) {
        messages.value.push({
          role: 'assistant',
          content: nodeOutput.process_result,
          agentName: 'process',
          timestamp: Date.now(),
        })
      }

      // supervisor 노드: final_answer
      if (nodeOutput.final_answer && nodeName !== 'chat') {
        messages.value.push({
          role: 'assistant',
          content: nodeOutput.final_answer,
          agentName: 'supervisor',
          timestamp: Date.now(),
        })
      }

      // reject로 인한 final_answer (router_hitl 노드에서 직접 설정)
      if (nodeName === 'router_hitl' && nodeOutput.final_answer) {
        // 이미 위에서 처리됨 — 중복 방지
      }
    }
  }

  // ─── Human-in-the-loop 핸들러 ──────────────────────────────

  async function handleApprove(simulateToolResult) {
    pendingApproval.value = null
    isLoading.value = true

    messages.value.push({
      role: 'system',
      content: '요청을 승인했습니다. 공정 검사를 진행합니다.',
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
      content: `요청을 거부했습니다: ${reason}`,
      timestamp: Date.now(),
    })

    if (props.isConnected) {
      await client.rejectToolCall(props.threadId, reason, makeStreamCallbacks())
    } else {
      isLoading.value = false
    }
  }

  async function handleEdit(toolCallId, newArgs, simulateToolResult) {
    pendingApproval.value = null
    isLoading.value = true

    messages.value.push({
      role: 'system',
      content: '요청을 수정 후 진행합니다.',
      timestamp: Date.now(),
    })

    if (props.isConnected) {
      await client.editToolCall(props.threadId, newArgs, makeStreamCallbacks())
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
