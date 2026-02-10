<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  message: Object,
  index: Number,
})

marked.setOptions({
  breaks: true,
  gfm: true,
})

const isUser = computed(() => props.message.role === 'user')
const isAssistant = computed(() => props.message.role === 'assistant')
const isTool = computed(() => props.message.role === 'tool')
const isSystem = computed(() => props.message.role === 'system')

const renderedContent = computed(() => {
  if (!props.message.content) return ''
  return marked.parse(props.message.content)
})

const toolCallsList = computed(() => props.message.toolCalls || [])

const animDelay = computed(() => `${Math.min(props.index * 0.05, 0.3)}s`)
</script>

<template>
  <div
    class="message-row"
    :class="{
      'user': isUser,
      'assistant': isAssistant,
      'tool': isTool,
      'system': isSystem,
    }"
    :style="{ animationDelay: animDelay }"
  >
    <!-- Avatar -->
    <div class="avatar" v-if="!isUser">
      <template v-if="isAssistant">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <rect x="2" y="2" width="14" height="14" rx="3" stroke="var(--accent)" stroke-width="1.2"/>
          <circle cx="9" cy="9" r="2.5" fill="var(--accent)"/>
        </svg>
      </template>
      <template v-else-if="isTool">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M7 3L11 9L7 15" stroke="var(--text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </template>
      <template v-else>
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <circle cx="9" cy="9" r="7" stroke="var(--text-tertiary)" stroke-width="1.2"/>
          <path d="M6 9H12" stroke="var(--text-tertiary)" stroke-width="1.2" stroke-linecap="round"/>
        </svg>
      </template>
    </div>

    <div class="bubble-wrapper">
      <!-- Agent name label -->
      <div class="msg-label" v-if="isAssistant && message.agentName">
        {{ message.agentName }}
      </div>
      <div class="msg-label tool-label" v-if="isTool && message.toolName">
        {{ message.toolName }} 결과
      </div>

      <!-- Bubble content -->
      <div class="bubble">
        <div
          v-if="message.content"
          class="bubble-content"
          v-html="renderedContent"
        />

        <!-- Tool calls inside assistant message -->
        <div v-if="toolCallsList.length" class="tool-calls-preview">
          <div v-for="tc in toolCallsList" :key="tc.id" class="tc-item">
            <span class="tc-icon">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M2 6H10M7 3L10 6L7 9" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
            <span class="tc-name">{{ tc.name }}</span>
            <span class="tc-args" v-if="tc.args">{{ typeof tc.args === 'string' ? tc.args : JSON.stringify(tc.args) }}</span>
          </div>
        </div>
      </div>

      <!-- Timestamp -->
      <div class="msg-time" v-if="message.timestamp">
        {{ new Date(message.timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.message-row {
  display: flex;
  gap: 0.65rem;
  padding: 0.4rem 0;
  animation: fadeInUp 0.35s var(--ease-out) both;
  max-width: 85%;
}

.message-row.user {
  margin-left: auto;
  flex-direction: row-reverse;
}

.message-row.tool {
  max-width: 90%;
}

/* Avatar */
.avatar {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  margin-top: 0.2rem;
}

.message-row.assistant .avatar {
  border-color: var(--border-accent);
  background: var(--accent-glow);
}

/* Labels */
.msg-label {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 500;
  color: var(--accent-dim);
  letter-spacing: 0.04em;
  margin-bottom: 0.25rem;
  text-transform: uppercase;
}

.msg-label.tool-label {
  color: var(--text-tertiary);
}

/* Bubble */
.bubble-wrapper {
  min-width: 0;
}

.bubble {
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  font-size: 0.88rem;
  line-height: 1.65;
  word-break: break-word;
}

.message-row.user .bubble {
  background: var(--accent);
  color: var(--text-inverse);
  border-radius: var(--radius-md) var(--radius-md) 4px var(--radius-md);
}

.message-row.assistant .bubble {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  color: var(--text-primary);
  border-radius: var(--radius-md) var(--radius-md) var(--radius-md) 4px;
}

.message-row.tool .bubble {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 0.78rem;
  border-radius: var(--radius-sm);
}

.message-row.system .bubble {
  background: var(--warning-glow);
  border: 1px solid rgba(255, 178, 36, 0.15);
  color: var(--warning);
  font-size: 0.82rem;
  text-align: center;
}

/* Markdown content */
.bubble-content :deep(p) {
  margin: 0;
}

.bubble-content :deep(p + p) {
  margin-top: 0.5em;
}

.bubble-content :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.82em;
  padding: 0.15em 0.4em;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 4px;
}

.bubble-content :deep(pre) {
  margin: 0.5em 0;
  padding: 0.75em;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow-x: auto;
}

.bubble-content :deep(pre code) {
  background: transparent;
  padding: 0;
}

.bubble-content :deep(ul), .bubble-content :deep(ol) {
  padding-left: 1.2em;
  margin: 0.3em 0;
}

.bubble-content :deep(strong) {
  color: var(--accent);
  font-weight: 600;
}

/* Tool calls preview */
.tool-calls-preview {
  margin-top: 0.6rem;
  padding-top: 0.6rem;
  border-top: 1px solid var(--border);
}

.tc-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem 0;
  font-family: var(--font-mono);
  font-size: 0.75rem;
}

.tc-icon {
  color: var(--warning);
  flex-shrink: 0;
}

.tc-name {
  color: var(--warning);
  font-weight: 600;
}

.tc-args {
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
}

/* Timestamp */
.msg-time {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  color: var(--text-tertiary);
  margin-top: 0.25rem;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.message-row:hover .msg-time {
  opacity: 1;
}
</style>
