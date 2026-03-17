<template>
  <div class="chat-stream" ref="streamEl">
    <div v-if="messages.length === 0" class="chat-empty">
      <div class="empty-glyph">◈</div>
      <p class="empty-title">분석 대기 중</p>
      <p class="empty-sub">에이전트를 실행하면 결과가 순서대로 표시됩니다</p>
    </div>

    <div class="bubbles-wrap">
      <template v-for="msg in messages" :key="msg.id">

        <!-- 사용자 입력 메시지 (기존 그대로) -->
        <div v-if="msg.agentKey === 'user'" class="user-bubble">
          <span class="user-bubble-text">{{ msg.userText }}</span>
        </div>

        <!-- system 계열 버블 (신규) -->
        <div v-else-if="msg.agentKey === 'system'" class="system-bubble">

          <!-- 단순 안내 텍스트 -->
          <template v-if="msg.status === 'system'">
            <p class="system-text">{{ msg.text }}</p>
          </template>

          <!-- 가설 선택 버튼 목록 -->
          <template v-else-if="msg.status === 'hypothesis_select'">
            <p class="system-label">가설을 선택하세요</p>
            <div class="hypothesis-btn-list">
              <button
                v-for="(h, i) in msg.hypotheses"
                :key="i"
                class="hypothesis-btn"
                :class="{ done: msg.done }"
                :disabled="msg.done"
                @click="!msg.done && $emit('select-hypothesis', h)"
              >
                {{ h.text }}
              </button>
            </div>
          </template>

          <!-- 에이전트 선택 체크박스 + 실행 버튼 -->
          <template v-else-if="msg.status === 'agent_select'">
            <p class="system-label">분석할 에이전트를 선택하세요</p>
            <div class="agent-check-list">
              <label
                v-for="a in msg.agents"
                :key="a.key"
                class="agent-check-item"
                :class="{ done: msg.done }"
              >
                <input
                  type="checkbox"
                  :checked="msg.enabledAgents[a.key]"
                  :disabled="msg.done"
                  @change="msg.enabledAgents[a.key] = $event.target.checked"
                />
                <span class="agent-check-icon">{{ a.icon }}</span>
                <span class="agent-check-label">{{ a.label }}</span>
              </label>
            </div>
            <button
              class="run-agents-btn"
              :disabled="msg.done"
              @click="!msg.done && $emit('run-agents', msg)"
            >
              {{ msg.done ? '실행됨' : '분석 실행' }}
            </button>
          </template>

          <!-- 최종 액션 플랜 -->
          <template v-else-if="msg.status === 'final_plan'">
            <p class="system-label">최종 액션 플랜</p>
            <div class="analysis-text" v-html="renderMarkdown(msg.text)"></div>
          </template>

        </div>

        <!-- 에이전트 결과 메시지 (기존 그대로) -->
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

defineEmits(['select-hypothesis', 'run-agents'])

const streamEl = ref(null)

watch(() => props.messages.length, async () => {
  await nextTick()
  if (streamEl.value) streamEl.value.scrollTop = streamEl.value.scrollHeight
})

const defaultColDef = { resizable: true, sortable: true, filter: true, flex: 1, minWidth: 80 }

function agentConf(key)  { return AGENT_CONFIG.find(a => a.key === key) }
function agentLabel(key) { return agentConf(key)?.label   || key }
function agentIcon(key)  { return agentConf(key)?.icon    || '🤖' }
function agentColor(key) { return agentConf(key)?.color   || '#60a5fa' }
function getColDefs(key) { return agentConf(key)?.colDefs || [] }
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

/* system 버블 */
.system-bubble {
  align-self: flex-start;
  max-width: 88%;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-left: 3px solid #3b82f6;
  border-radius: 8px;
  padding: 12px 16px;
  animation: bubbleIn 0.28s ease;
}

.system-text {
  font-size: 0.84rem;
  color: var(--text-2);
  line-height: 1.7;
}

.system-label {
  font-size: 0.72rem;
  color: var(--text-3);
  font-family: var(--mono);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.hypothesis-btn-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.hypothesis-btn {
  background: rgba(59, 130, 246, 0.06);
  border: 1px solid rgba(59, 130, 246, 0.25);
  border-radius: 7px;
  padding: 9px 14px;
  color: #93c5fd;
  font-size: 0.83rem;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  line-height: 1.5;
}

.hypothesis-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.14);
  border-color: rgba(59, 130, 246, 0.5);
}

.hypothesis-btn.done,
.hypothesis-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.agent-check-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.agent-check-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 0.83rem;
  color: var(--text-2);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 6px 12px;
  transition: border-color 0.15s;
}

.agent-check-item:not(.done):hover {
  border-color: var(--border-mid);
}

.agent-check-item.done {
  opacity: 0.45;
  cursor: not-allowed;
}

.agent-check-item input[type="checkbox"] {
  accent-color: #3b82f6;
  cursor: pointer;
}

.agent-check-icon { font-size: 0.9rem; }
.agent-check-label { font-size: 0.82rem; }

.run-agents-btn {
  background: #1d4ed8;
  color: #fff;
  border: none;
  border-radius: 7px;
  padding: 8px 20px;
  font-size: 0.84rem;
  cursor: pointer;
  transition: background 0.18s, opacity 0.18s;
  font-weight: 600;
}

.run-agents-btn:hover:not(:disabled) { background: #2563eb; }

.run-agents-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
