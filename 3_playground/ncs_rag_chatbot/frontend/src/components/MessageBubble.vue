<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  message: Object,
  index: Number,
})

marked.setOptions({ breaks: true, gfm: true })

const isUser = computed(() => props.message.role === 'user')
const isAssistant = computed(() => props.message.role === 'assistant')
const isSystem = computed(() => props.message.role === 'system')

const renderedContent = computed(() => {
  if (!props.message.content) return ''
  return marked.parse(props.message.content)
})

const sources = computed(() => props.message.sources || [])
const filterApplied = computed(() => props.message.filter)

const animDelay = computed(() => `${Math.min(props.index * 0.05, 0.3)}s`)
</script>

<template>
  <div
    class="message-row"
    :class="{ user: isUser, assistant: isAssistant, system: isSystem }"
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
      <template v-else>
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <circle cx="9" cy="9" r="7" stroke="var(--text-tertiary)" stroke-width="1.2"/>
          <path d="M6 9H12" stroke="var(--text-tertiary)" stroke-width="1.2" stroke-linecap="round"/>
        </svg>
      </template>
    </div>

    <div class="bubble-wrapper">
      <!-- Filter indicator -->
      <div class="filter-indicator" v-if="isAssistant && filterApplied">
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M1 1.5h8L6 5v3l-2 1V5L1 1.5z" stroke="currentColor" stroke-width="0.9" stroke-linejoin="round"/>
        </svg>
        필터 적용됨
      </div>

      <!-- Bubble -->
      <div class="bubble">
        <div
          v-if="message.content"
          class="bubble-content"
          v-html="renderedContent"
        />
      </div>

      <!-- Source cards -->
      <div v-if="sources.length" class="sources-section">
        <div class="sources-label">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <rect x="1.5" y="1.5" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1"/>
            <path d="M4 4h4M4 6h3M4 8h2" stroke="currentColor" stroke-width="0.8" stroke-linecap="round"/>
          </svg>
          참고 문서 {{ sources.length }}건
        </div>
        <div class="source-cards">
          <div v-for="(src, i) in sources" :key="i" class="source-card">
            <div class="source-meta">
              <span class="source-badge main">{{ src.main_category }}</span>
              <span class="source-badge sub">{{ src.sub_category }}</span>
              <span class="source-page">p.{{ src.page + 1 }}</span>
            </div>
            <div class="source-filename">{{ src.source }}</div>
            <div class="source-preview">{{ src.content }}</div>
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

/* Filter indicator */
.filter-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-family: var(--font-mono);
  font-size: 0.6rem;
  color: var(--accent-dim);
  margin-bottom: 0.25rem;
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

.message-row.system .bubble {
  background: var(--warning-glow);
  border: 1px solid rgba(255, 178, 36, 0.15);
  color: var(--warning);
  font-size: 0.82rem;
  text-align: center;
}

/* Markdown */
.bubble-content :deep(p) { margin: 0; }
.bubble-content :deep(p + p) { margin-top: 0.5em; }

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

/* Source cards */
.sources-section {
  margin-top: 0.6rem;
  animation: fadeIn 0.4s ease both 0.2s;
}

.sources-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--text-tertiary);
  margin-bottom: 0.4rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.source-cards {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.source-card {
  padding: 0.6rem 0.75rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  transition: all 0.2s ease;
}

.source-card:hover {
  border-color: var(--border-accent);
  background: var(--bg-hover);
}

.source-meta {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-bottom: 0.3rem;
  flex-wrap: wrap;
}

.source-badge {
  font-family: var(--font-mono);
  font-size: 0.58rem;
  font-weight: 600;
  padding: 0.12rem 0.4rem;
  border-radius: 100px;
  letter-spacing: 0.02em;
}

.source-badge.main {
  background: rgba(0, 229, 200, 0.12);
  color: var(--accent);
  border: 1px solid rgba(0, 229, 200, 0.2);
}

.source-badge.sub {
  background: rgba(255, 178, 36, 0.1);
  color: var(--warning);
  border: 1px solid rgba(255, 178, 36, 0.15);
}

.source-page {
  font-family: var(--font-mono);
  font-size: 0.58rem;
  color: var(--text-tertiary);
}

.source-filename {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 0.3rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.source-preview {
  font-size: 0.72rem;
  color: var(--text-tertiary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
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
