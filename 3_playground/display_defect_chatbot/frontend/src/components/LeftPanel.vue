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
        role="button"
        tabindex="0"
        @click="$emit('load-session', session.id)"
        @keydown.enter.prevent="$emit('load-session', session.id)"
      >
        <div class="card-top">
          <!-- 편집 모드 -->
          <input
            v-if="editingId === session.id"
            :ref="el => { if (el) editInputEl = el }"
            v-model="editTitle"
            class="title-edit-input"
            @keydown.enter.prevent="commitEdit(session)"
            @keydown.escape.prevent="cancelEdit"
            @blur="commitEdit(session)"
            @click.stop
          />
          <!-- 표시 모드 -->
          <span
            v-else
            class="session-title"
            :title="session.title"
            @dblclick.stop="startEdit(session)"
          >{{ session.title || session.productId || '-' }}</span>
          <button
            class="btn-delete"
            :aria-label="`세션 삭제: ${session.title || session.id}`"
            :title="`세션 삭제: ${session.title || session.id}`"
            @click.stop="$emit('delete-session', session.id)"
          >🗑</button>
        </div>
        <div class="card-time">{{ formatDate(session.updatedAt) }}</div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  activeSessionId: { type: [String, null], default: null },
})
const emit = defineEmits(['new-analysis', 'load-session', 'delete-session', 'update-title'])

// ── 인라인 제목 편집 상태 ───────────────────────────────────────────────────
const editingId = ref(null)
const editTitle = ref('')
let editInputEl = null

async function startEdit(session) {
  editingId.value = session.id
  editTitle.value = session.title
  await nextTick()
  editInputEl?.focus()
  editInputEl?.select()
}

async function commitEdit(session) {
  if (editingId.value !== session.id) return
  editingId.value = null
  const newTitle = editTitle.value.trim()
  if (newTitle && newTitle !== session.title) {
    emit('update-title', { id: session.id, title: newTitle })
  }
}

function cancelEdit() {
  editingId.value = null
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
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
  height: 100%;
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
.session-card:focus-visible {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}
.session-card.active { border-color: #3b82f6; background: #0f1c35; }

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

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

.card-time { font-size: 0.72rem; color: #4b5563; margin-top: 6px; }

.session-title {
  font-size: 0.82rem;
  color: #cbd5e1;
  font-weight: 500;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: default;
}
.session-title:hover { color: #e2e8f0; }

.title-edit-input {
  flex: 1;
  background: #1e293b;
  border: 1px solid #3b82f6;
  border-radius: 4px;
  color: #e0e0e0;
  font-size: 0.82rem;
  padding: 1px 6px;
  outline: none;
  min-width: 0;
}
</style>
