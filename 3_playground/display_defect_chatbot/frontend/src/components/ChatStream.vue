<template>
  <div class="chat-stream" ref="streamEl">
    <div v-if="messages.length === 0" class="chat-empty">
      에이전트를 실행하면 분석 결과가 여기에 표시됩니다.
    </div>

    <div v-for="msg in messages" :key="msg.id" class="chat-bubble">
      <!-- 말풍선 헤더 -->
      <div class="bubble-header">
        <span class="agent-avatar">🤖</span>
        <span class="agent-label">{{ agentLabel(msg.agentKey) }}</span>
        <span v-if="msg.status === 'loading'" class="spinner-sm"></span>
        <span v-else-if="msg.status === 'done'" class="badge-done">완료</span>
        <span v-else-if="msg.status === 'error'" class="badge-error">오류</span>
      </div>

      <!-- 로딩 중 -->
      <div v-if="msg.status === 'loading'" class="bubble-body loading-body">
        분석 중...
      </div>

      <!-- 완료 -->
      <div v-else-if="msg.status === 'done' && msg.result" class="bubble-body">
        <div class="analysis-text">{{ msg.result.analysis }}</div>

        <template v-if="msg.result.suspectRows?.length">
          <div class="grid-label">의심 데이터</div>
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

      <!-- 오류 -->
      <div v-else-if="msg.status === 'error'" class="bubble-body error-body">
        분석 중 오류가 발생했습니다.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community'
import { AGENT_CONFIG } from '../composables/useDefectChat.js'

ModuleRegistry.registerModules([AllCommunityModule])

const props = defineProps({
  messages: { type: Array, default: () => [] },
})

const streamEl = ref(null)

// 새 메시지 추가 시 스크롤 하단으로
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
  test_result: [
    { field: 'test_type', headerName: '테스트 유형' },
    { field: 'result', headerName: '결과', cellClass: p => p.value === 'FAIL' ? 'cell-fail' : 'cell-pass' },
    { field: 'measured_value', headerName: '측정값' },
    { field: 'spec_min', headerName: '최소규격' },
    { field: 'spec_max', headerName: '최대규격' },
    { field: 'tested_at', headerName: '측정시간' },
  ],
}

function getColDefs(agentKey) { return COL_DEFS[agentKey] || [] }

function agentLabel(agentKey) {
  return AGENT_CONFIG.find(a => a.key === agentKey)?.label || agentKey
}
</script>

<style>
/* AG Grid 셀 색상 (전역 — scoped 밖에서만 동작) */
.cell-fail { color: #f87171 !important; font-weight: 600; }
.cell-pass { color: #4ade80 !important; }
.cell-warn { color: #fbbf24 !important; }
</style>

<style scoped>
.chat-stream {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-empty {
  color: #4b5563;
  font-size: 0.85rem;
  text-align: center;
  margin-top: 40px;
}

.chat-bubble {
  background: #1a1d27;
  border: 1px solid #2a2d3a;
  border-radius: 12px;
  overflow: hidden;
}

.bubble-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid #2a2d3a;
  background: #1e2130;
}
.agent-avatar { font-size: 1rem; }
.agent-label { font-size: 0.85rem; color: #93c5fd; font-weight: 600; flex: 1; }

.badge-done {
  font-size: 0.7rem; padding: 2px 8px; border-radius: 4px;
  background: #064e3b; color: #6ee7b7;
}
.badge-error {
  font-size: 0.7rem; padding: 2px 8px; border-radius: 4px;
  background: #7f1d1d; color: #fca5a5;
}

.bubble-body { padding: 14px; }
.loading-body { color: #6b7280; font-size: 0.85rem; font-style: italic; }
.error-body { color: #f87171; font-size: 0.85rem; }

.analysis-text {
  color: #d1d5db;
  font-size: 0.85rem;
  line-height: 1.7;
  margin-bottom: 12px;
  white-space: pre-wrap;
}

.grid-label { color: #6b7280; font-size: 0.75rem; margin-bottom: 6px; }
.grid-box { border-radius: 6px; overflow: hidden; font-size: 0.78rem; }
.no-data { color: #4b5563; font-size: 0.82rem; margin: 0; }

.spinner-sm {
  width: 12px; height: 12px;
  border: 2px solid #374151;
  border-top-color: #60a5fa;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
