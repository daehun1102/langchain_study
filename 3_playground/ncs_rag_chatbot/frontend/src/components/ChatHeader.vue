<script setup>
import { computed } from 'vue'

const props = defineProps({
  isConnected: Boolean,
  activeFilter: Object,
})

const filterLabel = computed(() => {
  if (!props.activeFilter?.mainCategory) return null
  let label = props.activeFilter.mainCategory
  if (props.activeFilter.subCategory) {
    label += ` › ${props.activeFilter.subCategory}`
  }
  return label
})
</script>

<template>
  <header class="chat-header">
    <div class="header-left">
      <div class="header-dot active" />
      <div class="header-info">
        <span class="header-title">NCS Knowledge Agent</span>
        <span class="header-sub">국가직무능력표준 RAG 검색</span>
      </div>
    </div>
    <div class="header-right">
      <div v-if="filterLabel" class="filter-badge">
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M1 1.5h8L6 5v3l-2 1V5L1 1.5z" stroke="currentColor" stroke-width="0.9" stroke-linejoin="round"/>
        </svg>
        {{ filterLabel }}
      </div>
      <div class="header-badge" :class="isConnected ? 'live' : 'demo'">
        {{ isConnected ? 'LIVE' : 'OFFLINE' }}
      </div>
    </div>
  </header>
</template>

<style scoped>
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.5rem;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(12px);
  z-index: 5;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.header-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-tertiary);
}

.header-dot.active {
  background: var(--accent);
  box-shadow: 0 0 10px var(--accent);
  animation: pulse 2.5s ease-in-out infinite;
}

.header-info {
  display: flex;
  flex-direction: column;
}

.header-title {
  font-weight: 600;
  font-size: 0.9rem;
}

.header-sub {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--text-tertiary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 500;
  padding: 0.25rem 0.65rem;
  border-radius: 100px;
  background: var(--accent-glow);
  color: var(--accent);
  border: 1px solid var(--border-accent);
}

.header-badge {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  padding: 0.25rem 0.65rem;
  border-radius: 100px;
}

.header-badge.live {
  background: var(--success-glow);
  color: var(--success);
  border: 1px solid rgba(0, 214, 143, 0.3);
}

.header-badge.demo {
  background: var(--warning-glow);
  color: var(--warning);
  border: 1px solid rgba(255, 178, 36, 0.3);
}
</style>
