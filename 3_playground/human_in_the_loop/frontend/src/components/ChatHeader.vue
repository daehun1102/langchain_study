<script setup>
defineProps({
  threadId: String,
  isConnected: Boolean,
})
</script>

<template>
  <header class="chat-header">
    <div class="header-left">
      <div class="header-dot active" />
      <div class="header-info">
        <span class="header-title">Semiconductor QC Agent</span>
        <span class="header-id">{{ threadId.slice(0, 12) }}...</span>
      </div>
    </div>
    <div class="header-right">
      <div class="header-badge" :class="isConnected ? 'live' : 'demo'">
        {{ isConnected ? 'LIVE' : 'DEMO' }}
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

.header-id {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--text-tertiary);
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
