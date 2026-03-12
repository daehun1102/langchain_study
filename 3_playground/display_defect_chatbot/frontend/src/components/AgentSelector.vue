<template>
  <div class="agent-selector">
    <div class="hyp-banner">
      <span class="banner-label">HYPOTHESIS</span>
      <span class="banner-text">{{ hypothesis }}</span>
    </div>

    <div class="view-header">
      <span class="tag-mono">// AGENT.CONFIG</span>
      <h2>분석 에이전트 선택</h2>
      <p class="subtitle">실행할 에이전트를 선택하고 분석을 시작하세요.</p>
    </div>

    <div class="agent-grid">
      <button
        v-for="agent in agents"
        :key="agent.key"
        class="agent-card"
        :class="{ active: enabledAgents[agent.key] }"
        :style="{ '--ac': agentColor(agent.key) }"
        @click="$emit('toggle', agent.key)"
      >
        <div class="card-accent"></div>
        <div class="card-top">
          <span class="agent-icon">{{ agent.icon }}</span>
          <span class="agent-label">{{ agent.label }}</span>
          <span class="toggle-pill" :class="enabledAgents[agent.key] ? 'on' : 'off'">
            {{ enabledAgents[agent.key] ? 'ON' : 'OFF' }}
          </span>
        </div>
        <p class="agent-desc">{{ agent.desc }}</p>
      </button>
    </div>

    <div class="action-row">
      <button class="btn-back" :disabled="loading" @click="$emit('back')">
        ← 가설 다시 선택
      </button>
      <button
        class="btn-run"
        :disabled="loading || enabledCount === 0"
        @click="$emit('run-all')"
      >
      <span v-if="loading" class="run-spinner"></span>
      <svg v-else viewBox="0 0 16 16" fill="currentColor" width="15" height="15">
        <path d="M5 3.5a.5.5 0 01.763-.424l8 4.5a.5.5 0 010 .848l-8 4.5A.5.5 0 015 12.5v-9z"/>
      </svg>
        {{ loading ? '분석 실행 중...' : `선택된 에이전트 실행 (${enabledCount}개)` }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { AGENT_CONFIG } from '../composables/useDefectChat.js'

const props = defineProps(['hypothesis', 'enabledAgents', 'loading'])
defineEmits(['toggle', 'run-all', 'back'])

const agents = AGENT_CONFIG
const enabledCount = computed(() => Object.values(props.enabledAgents).filter(Boolean).length)

const COLORS = {
  process_history: '#00c8ff',
  return_history:  '#f59e0b',
  test_history:    '#10b981',
  long_term:       '#a78bfa',
}
function agentColor(key) { return COLORS[key] || '#60a5fa' }
</script>

<style scoped>
.agent-selector {
  max-width: 760px;
  margin: 0 auto;
  animation: fadeUp 0.3s ease;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

.hyp-banner {
  display: flex;
  align-items: baseline;
  gap: 12px;
  background: rgba(0, 200, 255, 0.04);
  border: 1px solid rgba(0, 200, 255, 0.12);
  border-left: 3px solid var(--ac-cyan);
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 24px;
  overflow: hidden;
}

.banner-label {
  font-family: var(--mono);
  font-size: 0.6rem;
  color: var(--ac-cyan);
  letter-spacing: 0.12em;
  white-space: nowrap;
  flex-shrink: 0;
  opacity: 0.7;
}

.banner-text {
  font-size: 0.83rem;
  color: var(--text-2);
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
}

.view-header { margin-bottom: 20px; }

.tag-mono {
  display: inline-block;
  font-family: var(--mono);
  font-size: 0.68rem;
  color: var(--ac-cyan);
  letter-spacing: 0.1em;
  margin-bottom: 8px;
  opacity: 0.75;
}

h2 {
  font-family: var(--sans);
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--text-1);
  margin-bottom: 5px;
}

.subtitle {
  font-size: 0.78rem;
  color: var(--text-3);
}

.agent-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 18px;
}

.agent-card {
  position: relative;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 14px 14px 18px;
  cursor: pointer;
  text-align: left;
  font-family: var(--sans);
  transition: border-color 0.18s, background 0.18s, box-shadow 0.18s;
  overflow: hidden;
}

.agent-card:hover {
  border-color: var(--ac);
  background: rgba(255, 255, 255, 0.02);
}

.agent-card.active {
  border-color: var(--ac);
  box-shadow: 0 0 0 1px rgba(var(--ac), 0.15);
}

.card-accent {
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  background: var(--ac);
  border-radius: 10px 0 0 10px;
  opacity: 0;
  transition: opacity 0.18s;
}

.agent-card.active .card-accent { opacity: 1; }

.card-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.agent-icon { font-size: 1.15rem; }

.agent-label {
  flex: 1;
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-1);
}

.toggle-pill {
  font-family: var(--mono);
  font-size: 0.6rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 3px;
  letter-spacing: 0.08em;
  transition: background 0.18s, color 0.18s;
}

.toggle-pill.on {
  background: rgba(0, 200, 255, 0.12);
  color: var(--ac);
  border: 1px solid rgba(0, 200, 255, 0.25);
}

.agent-card[style*="f59e0b"] .toggle-pill.on {
  background: rgba(245, 158, 11, 0.12);
  color: var(--ac);
  border-color: rgba(245, 158, 11, 0.25);
}

.toggle-pill.off {
  background: transparent;
  color: var(--text-3);
  border: 1px solid var(--border);
}

.agent-desc {
  font-size: 0.75rem;
  color: var(--text-3);
  line-height: 1.55;
  margin: 0;
}

.agent-card.active .agent-desc { color: var(--text-2); }

.action-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.btn-back {
  flex-shrink: 0;
  background: transparent;
  color: var(--text-3);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 13px 16px;
  font-family: var(--sans);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.18s, border-color 0.18s;
  white-space: nowrap;
}

.btn-back:hover:not(:disabled) {
  color: var(--text-1);
  border-color: var(--text-3);
}

.btn-back:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-run {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  background: var(--ac-cyan);
  color: #060b12;
  border: none;
  border-radius: 8px;
  padding: 13px 20px;
  font-family: var(--sans);
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.18s, box-shadow 0.18s, opacity 0.18s;
  letter-spacing: 0.02em;
}

.btn-run:hover:not(:disabled) {
  background: #2dd4f0;
  box-shadow: 0 0 24px rgba(0, 200, 255, 0.28);
}

.btn-run:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.run-spinner {
  width: 13px;
  height: 13px;
  border: 2px solid rgba(6, 11, 18, 0.25);
  border-top-color: #060b12;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
