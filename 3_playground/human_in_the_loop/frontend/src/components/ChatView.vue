<script setup>
import MessageBubble from './MessageBubble.vue'
import HumanApproval from './HumanApproval.vue'
import ChatInput from './ChatInput.vue'
import ChatHeader from './ChatHeader.vue'
import WelcomeMessage from './WelcomeMessage.vue'
import TypingIndicator from './TypingIndicator.vue'
import { useChat } from '../composables/useChat.js'
import { useDemoMode } from '../composables/useDemoMode.js'

const props = defineProps({
  threadId: String,
  isConnected: Boolean,
})

const {
  messages,
  isLoading,
  pendingApproval,
  scrollContainer,
  sendMessage,
  handleApprove,
  handleReject,
  handleEdit,
} = useChat(props)

const { simulateResponse, simulateToolResult } = useDemoMode(
  messages,
  isLoading,
  pendingApproval,
)

function onSendMessage(text) {
  sendMessage(text, simulateResponse)
}

function onApprove() {
  handleApprove(simulateToolResult)
}

function onReject(reason) {
  handleReject(reason)
}

function onEdit(toolCallId, newArgs) {
  handleEdit(toolCallId, newArgs, simulateToolResult)
}
</script>

<template>
  <div class="chat-view">
    <ChatHeader :threadId="threadId" :isConnected="isConnected" />

    <div class="messages-scroll" ref="scrollContainer">
      <div class="messages-inner">
        <WelcomeMessage v-if="!messages.length" @send="onSendMessage" />

        <MessageBubble
          v-for="(msg, i) in messages"
          :key="i"
          :message="msg"
          :index="i"
        />

        <TypingIndicator v-if="isLoading" />

        <HumanApproval
          v-if="pendingApproval"
          :toolCalls="pendingApproval.toolCalls"
          :description="pendingApproval.description"
          @approve="onApprove"
          @reject="onReject"
          @edit="onEdit"
        />
      </div>
    </div>

    <ChatInput
      :disabled="!!pendingApproval"
      :loading="isLoading"
      @send="onSendMessage"
    />
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

.messages-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem 1.5rem;
}

.messages-inner {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
</style>
