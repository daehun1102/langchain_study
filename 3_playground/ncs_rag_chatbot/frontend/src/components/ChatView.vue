<script setup>
import MessageBubble from './MessageBubble.vue'
import ChatInput from './ChatInput.vue'
import ChatHeader from './ChatHeader.vue'
import WelcomeMessage from './WelcomeMessage.vue'
import TypingIndicator from './TypingIndicator.vue'
import { useChat } from '../composables/useChat.js'
import { watch } from 'vue'

const props = defineProps({
  isConnected: Boolean,
  activeFilter: Object,
})

const {
  messages,
  isLoading,
  scrollContainer,
  setFilter,
  sendMessage,
} = useChat()

// Sync filter from parent
watch(
  () => props.activeFilter,
  (f) => setFilter(f.mainCategory, f.subCategory),
  { deep: true, immediate: true },
)

function onSendMessage(text) {
  sendMessage(text)
}
</script>

<template>
  <div class="chat-view">
    <ChatHeader :isConnected="isConnected" :activeFilter="activeFilter" />

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
      </div>
    </div>

    <ChatInput
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
