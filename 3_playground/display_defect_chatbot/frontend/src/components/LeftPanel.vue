<template>
  <aside class="left-panel">
    <div class="panel-header">
      <h2>분석 이력</h2>
      <button class="btn-new" @click="$emit('new-analysis')">+ 새 분석</button>
    </div>

    <div class="session-list">
      <p v-if="sessions.length === 0" class="empty-hint">분석 이력이 없습니다.</p>

      <div
        v-for="session in sessions"
        :key="session.id"
        class="session-card"
        :class="{ active: session.id === activeSessionId }"
        @click="$emit('load-session', session)"
      >
        <div class="card-top">
          <span class="product-id">{{ session.productId || '-' }}</span>
          <button class="btn-delete" @click.stop="$emit('delete-session', session.id)">🗑</button>
        </div>
        <p class="defect-desc">{{ truncate(session.defectDescription) }}</p>
        <div class="card-bottom">
          <span class="agent-icons">
            <span v-for="agent in ranAgents(session)" :key="agent.key">{{ agent.icon }}</span>
          </span>
          <span class="timestamp">{{ formatDate(session.timestamp) }}</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { AGENT_CONFIG } from '../composables/useDefectChat.js'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  activeSessionId: { type: String, default: null },
})
defineEmits(['new-analysis', 'load-session', 'delete-session'])

function truncate(str) {
  if (!str) return '-'
  return str.length > 32 ? str.slice(0, 32) + '...' : str
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function ranAgents(session) {
  return AGENT_CONFIG.filter(a => session.agentResults?.[a.key])
}
</script>

<style scoped>
.left-panel {
  width: 280px;
  min-width: 280px;
  background: #1a1d27;
  border-right: 1px solid #2a2d3a;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #2a2d3a;
}
.panel-header h2 { font-size: 0.95rem; color: #60a5fa; }

.btn-new {
  background: #1d4ed8;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 0.78rem;
  cursor: pointer;
}
.btn-new:hover { background: #2563eb; }

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-hint { color: #4b5563; font-size: 0.82rem; text-align: center; margin-top: 24px; }

.session-card {
  background: #0f1117;
  border: 1px solid #2a2d3a;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.session-card:hover { border-color: #374151; }
.session-card.active { border-color: #3b82f6; background: #0f1c35; }

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.product-id { font-size: 0.85rem; color: #93c5fd; font-weight: 600; }

.btn-delete {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  opacity: 0.5;
  padding: 0;
  line-height: 1;
}
.btn-delete:hover { opacity: 1; }

.defect-desc { font-size: 0.78rem; color: #6b7280; margin-bottom: 8px; line-height: 1.4; }

.card-bottom { display: flex; align-items: center; justify-content: space-between; }
.agent-icons { font-size: 0.9rem; letter-spacing: 2px; }
.timestamp { font-size: 0.72rem; color: #4b5563; }
</style>
