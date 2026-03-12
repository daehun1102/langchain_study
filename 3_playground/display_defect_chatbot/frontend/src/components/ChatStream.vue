<template>
  <div class="chat-stream" ref="streamEl">
    <div v-if="messages.length === 0" class="chat-empty">
      <div class="empty-glyph">◈</div>
      <p class="empty-title">분석 대기 중</p>
      <p class="empty-sub">에이전트를 실행하면 결과가 순서대로 표시됩니다</p>
    </div>

    <div class="bubbles-wrap">
      <template v-for="msg in messages" :key="msg.id">
        <!-- 사용자 입력 메시지 -->
        <div v-if="msg.agentKey === 'user'" class="user-bubble">
          <span class="user-bubble-text">{{ msg.userText }}</span>
        </div>

        <!-- 에이전트 결과 메시지 -->
        <div
          v-else
          class="chat-bubble"
          :style="{ '--ac': agentColor(msg.agentKey) }"
        >
          <div class="bubble-header">
            <span class="agent-dot">{{ agentIcon(msg.agentKey) }}</span>
            <span class="agent-name">{{ agentLabel(msg.agentKey) }}</span>

            <span v-if="msg.status === 'loading'" class="status-loading" aria-label="분석 중">
              <span></span><span></span><span></span>
            </span>
            <span v-else-if="msg.status === 'done'" class="status-badge done">완료</span>
            <span v-else-if="msg.status === 'error'" class="status-badge error">오류</span>
          </div>

          <div v-if="msg.status === 'loading'" class="bubble-body loading-body">
            <span class="loading-text">데이터 분석 중</span>
            <span class="loading-dots"><span></span><span></span><span></span></span>
          </div>

          <div v-else-if="msg.status === 'done' && msg.result" class="bubble-body">
            <div class="analysis-text" v-html="renderMarkdown(msg.result.analysis)"></div>

            <template v-if="msg.result.suspectRows?.length">
              <div class="grid-header">
                <span class="grid-label">의심 데이터</span>
                <span class="grid-count">{{ msg.result.suspectRows.length }}건</span>
              </div>
              <AgGridVue
                class="ag-theme-quartz-dark grid-box"
                :rowData="msg.result.suspectRows"
                :columnDefs="getColDefs(msg.agentKey)"
                :defaultColDef="defaultColDef"
                domLayout="autoHeight"
              />
            </template>
            <p v-else class="no-data">의심 데이터 없음</p>
          </div>

          <div v-else-if="msg.status === 'error'" class="bubble-body error-body">
            <span class="error-badge">!</span>
            분석 중 오류가 발생했습니다.
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community'
import { marked } from 'marked'
import { AGENT_CONFIG } from '../composables/useDefectChat.js'

marked.setOptions({ breaks: true })
function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(String(text))
}

ModuleRegistry.registerModules([AllCommunityModule])

const props = defineProps({
  messages: { type: Array, default: () => [] },
})

const streamEl = ref(null)

watch(() => props.messages.length, async () => {
  await nextTick()
  if (streamEl.value) streamEl.value.scrollTop = streamEl.value.scrollHeight
})

const defaultColDef = { resizable: true, sortable: true, filter: true, flex: 1, minWidth: 80 }

const COL_DEFS = {
  process_history: [
    { field: 'process_step', headerName: '공정단계' },
    { field: 'result', headerName: '결과', cellClass: p => p.value === 'FAIL' ? 'cell-fail' : 'cell-pass' },
    { field: 'equipment_id', headerName: '설비ID' },
    { field: 'operator_id', headerName: '작업자' },
    { field: 'measured_at', headerName: '측정시간' },
  ],
  return_history: [
    { field: 'return_reason', headerName: '반송 사유' },
    { field: 'severity', headerName: '심각도', cellClass: p => p.value === 'HIGH' ? 'cell-fail' : p.value === 'LOW' ? 'cell-pass' : 'cell-warn' },
    { field: 'quantity', headerName: '수량' },
    { field: 'return_date', headerName: '반송일' },
  ],
  test_history: [
    { field: 'test_type', headerName: '테스트 유형' },
    { field: 'result', headerName: '결과', cellClass: p => p.value === 'FAIL' ? 'cell-fail' : 'cell-pass' },
    { field: 'measured_value', headerName: '측정값' },
    { field: 'spec_min', headerName: '최소규격' },
    { field: 'spec_max', headerName: '최대규격' },
    { field: 'tested_at', headerName: '측정시간' },
  ],
}

function getColDefs(agentKey) { return COL_DEFS[agentKey] || [] }

const AGENT_COLORS = {
  process_history: '#00c8ff',
  return_history:  '#f59e0b',
  test_history:    '#10b981',
  long_term:       '#a78bfa',
}

function agentLabel(agentKey) { return AGENT_CONFIG.find(a => a.key === agentKey)?.label || agentKey }
function agentIcon(agentKey)  { return AGENT_CONFIG.find(a => a.key === agentKey)?.icon  || '🤖' }
function agentColor(agentKey) { return AGENT_COLORS[agentKey] || '#60a5fa' }
</script>

<style>
.cell-fail { color: #f87171 !important; font-weight: 600; }
.cell-pass { color: #4ade80 !important; }
.cell-warn { color: #fbbf24 !important; }
</style>

<style scoped>
.chat-stream {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: 60px 20px;
  text-align: center;
  gap: 8px;
}

.empty-glyph {
  font-size: 2.2rem;
  color: var(--border-mid);
  margin-bottom: 6px;
}

.empty-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-3);
}

.empty-sub {
  font-size: 0.76rem;
  color: #2a3a52;
  line-height: 1.6;
}

.bubbles-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: stretch;
}

.chat-bubble {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--ac);
  border-radius: 8px;
  overflow: hidden;
  animation: bubbleIn 0.28s ease;
}

@keyframes bubbleIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.bubble-header {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 14px;
  border-bottom: 1px solid var(--border);
  background: rgba(0, 0, 0, 0.18);
}

.agent-dot {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.88rem;
  flex-shrink: 0;
}

.agent-name {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--ac);
  flex: 1;
  letter-spacing: 0.03em;
  font-family: var(--sans);
}

.status-loading {
  display: flex;
  gap: 3px;
  align-items: center;
}

.status-loading span,
.loading-dots span {
  display: inline-block;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--ac);
  opacity: 0.4;
  animation: dotPulse 1.3s ease-in-out infinite;
}

.status-loading span:nth-child(2),
.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.status-loading span:nth-child(3),
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dotPulse {
  0%, 100% { opacity: 0.2; transform: scale(0.75); }
  50%       { opacity: 1;   transform: scale(1); }
}

.status-badge {
  font-family: var(--mono);
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  padding: 2px 7px;
  border-radius: 3px;
}

.status-badge.done {
  background: rgba(16, 185, 129, 0.1);
  color: var(--ac-emerald);
  border: 1px solid rgba(16, 185, 129, 0.22);
}

.status-badge.error {
  background: rgba(248, 113, 113, 0.1);
  color: var(--ac-red);
  border: 1px solid rgba(248, 113, 113, 0.22);
}

.bubble-body { padding: 13px 16px; }

.loading-body {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-3);
  font-size: 0.8rem;
  font-style: italic;
  padding: 11px 16px;
}

.loading-dots {
  display: flex;
  gap: 3px;
}

.loading-dots span { background: var(--text-3); }

.analysis-text {
  font-size: 0.84rem;
  color: var(--text-2);
  line-height: 1.8;
  margin-bottom: 14px;
}

.analysis-text :deep(p) { margin-bottom: 8px; }
.analysis-text :deep(p:last-child) { margin-bottom: 0; }
.analysis-text :deep(h1),
.analysis-text :deep(h2),
.analysis-text :deep(h3) {
  color: var(--text-1);
  font-weight: 600;
  margin: 12px 0 6px;
  line-height: 1.4;
}
.analysis-text :deep(h1) { font-size: 1rem; }
.analysis-text :deep(h2) { font-size: 0.92rem; }
.analysis-text :deep(h3) { font-size: 0.86rem; }
.analysis-text :deep(ul),
.analysis-text :deep(ol) {
  padding-left: 1.4em;
  margin-bottom: 8px;
}
.analysis-text :deep(li) { margin-bottom: 3px; }
.analysis-text :deep(strong) { color: var(--text-1); font-weight: 700; }
.analysis-text :deep(em) { color: var(--text-2); font-style: italic; }
.analysis-text :deep(code) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  padding: 1px 5px;
  font-family: var(--mono);
  font-size: 0.82em;
  color: #7dd3fc;
}
.analysis-text :deep(pre) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 10px 14px;
  overflow-x: auto;
  margin-bottom: 8px;
}
.analysis-text :deep(pre code) {
  background: none;
  border: none;
  padding: 0;
  font-size: 0.8rem;
  color: #94a3b8;
}
.analysis-text :deep(blockquote) {
  border-left: 3px solid var(--border-mid);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--text-3);
  font-style: italic;
}
.analysis-text :deep(hr) {
  border: none;
  border-top: 1px solid var(--border);
  margin: 10px 0;
}
.analysis-text :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
  margin-bottom: 8px;
}
.analysis-text :deep(th),
.analysis-text :deep(td) {
  border: 1px solid var(--border);
  padding: 5px 10px;
  text-align: left;
}
.analysis-text :deep(th) {
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-1);
  font-weight: 600;
}

.grid-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.grid-label {
  font-family: var(--mono);
  font-size: 0.67rem;
  color: var(--text-3);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.grid-count {
  font-family: var(--mono);
  font-size: 0.67rem;
  color: var(--ac);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-mid);
  border-radius: 3px;
  padding: 0 5px;
}

.grid-box {
  border-radius: 6px;
  overflow: hidden;
  font-size: 0.78rem;
}

.no-data {
  font-size: 0.78rem;
  color: var(--text-3);
  font-style: italic;
  margin: 0;
}

.error-body {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--ac-red);
  font-size: 0.82rem;
}

.error-badge {
  width: 17px;
  height: 17px;
  border-radius: 50%;
  border: 1.5px solid var(--ac-red);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.68rem;
  font-weight: 700;
  flex-shrink: 0;
}

.user-bubble {
  align-self: flex-end;
  max-width: 72%;
  background: rgba(0, 200, 255, 0.08);
  border: 1px solid rgba(0, 200, 255, 0.2);
  border-radius: 12px 12px 2px 12px;
  padding: 9px 14px;
  animation: bubbleIn 0.22s ease;
}

.user-bubble-text {
  font-size: 0.84rem;
  color: #c8eeff;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
