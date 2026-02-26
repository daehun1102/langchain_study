<script setup>
import MessageBubble from './MessageBubble.vue'
import ChatInput from './ChatInput.vue'
import TypingIndicator from './TypingIndicator.vue'
import { useFeedbackChat } from '../composables/useFeedbackChat.js'

const props = defineProps({
  version: { type: String, required: true },
  label: { type: String, required: true },
})

const {
  messages,
  isLoading,
  scrollContainer,
  resetThread,
  sendMessage,
} = useFeedbackChat(props.version)
</script>

<template>
  <div class="chat-panel">
    <header class="panel-header">
      <div class="header-left">
        <h3>{{ label }}</h3>
        <p>직원 이름이나 사번을 포함해 질문하세요</p>
      </div>
      <button class="new-chat-btn" @click="resetThread">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M2 7a5 5 0 1 1 5 5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
          <path d="M2 4.5V7H4.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        새 대화
      </button>
    </header>

    <div class="messages-scroll" ref="scrollContainer">
      <div class="messages-inner">
        <div v-if="!messages.length" class="empty-state">
          <div class="empty-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <rect x="6" y="6" width="36" height="36" rx="8" stroke="var(--accent)" stroke-width="1" opacity="0.3"/>
              <rect x="12" y="12" width="24" height="24" rx="5" stroke="var(--accent)" stroke-width="1" opacity="0.5"/>
              <path d="M19 19h10M19 24h7M19 29h8" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </div>
          <h3>NCS 과제 피드백 에이전트</h3>
          <p>직원 이름 또는 사번을 포함해 질문하세요.<br/>예: <em>EMP001의 NCS 과제 채점 결과를 피드백해줘</em></p>
        </div>

        <MessageBubble
          v-for="(msg, i) in messages"
          :key="i"
          :message="msg"
          :index="i"
        />

        <TypingIndicator v-if="isLoading" />
      </div>
    </div>

    <ChatInput :loading="isLoading" @send="sendMessage" />
  </div>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid var(--border, rgba(255,255,255,0.08));
  flex-shrink: 0;
}

.header-left h3 {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary, #e2e8f0);
  margin: 0 0 0.1rem;
}

.header-left p {
  font-size: 0.72rem;
  color: var(--text-secondary, #94a3b8);
  margin: 0;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.8rem;
  background: transparent;
  border: 1px solid var(--border, rgba(255,255,255,0.1));
  border-radius: 8px;
  color: var(--text-secondary, #94a3b8);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.new-chat-btn:hover {
  border-color: var(--accent, #00e5c8);
  color: var(--accent, #00e5c8);
}

.messages-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.25rem;
}

.messages-inner {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 2.5rem 1rem 2rem;
  animation: fadeInUp 0.6s ease both;
}

.empty-icon { margin-bottom: 0.25rem; }

.empty-state h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary, #e2e8f0);
}

.empty-state p {
  font-size: 0.85rem;
  color: var(--text-secondary, #94a3b8);
  text-align: center;
  line-height: 1.7;
}

.empty-state em {
  font-style: normal;
  color: var(--accent, #00e5c8);
}
</style>
