<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  toolCalls: {
    type: Array,
    default: () => [],
  },
  description: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['approve', 'reject', 'edit'])

const rejectReason = ref('')
const showRejectInput = ref(false)
const editMode = ref(false)
const editedArgs = ref('')
const activeToolIndex = ref(0)

const activeTool = computed(() => props.toolCalls[activeToolIndex.value])

const formattedArgs = computed(() => {
  if (!activeTool.value) return '{}'
  try {
    return JSON.stringify(activeTool.value.args, null, 2)
  } catch {
    return String(activeTool.value.args)
  }
})

function approve() {
  emit('approve')
}

function reject() {
  if (!showRejectInput.value) {
    showRejectInput.value = true
    return
  }
  emit('reject', rejectReason.value || '사용자가 거부했습니다.')
  showRejectInput.value = false
  rejectReason.value = ''
}

function startEdit() {
  editMode.value = true
  editedArgs.value = formattedArgs.value
}

function submitEdit() {
  try {
    const parsed = JSON.parse(editedArgs.value)
    emit('edit', activeTool.value.id, parsed)
    editMode.value = false
  } catch {
    // invalid JSON — 사용자에게 알림
  }
}

function cancelEdit() {
  editMode.value = false
}

function cancelReject() {
  showRejectInput.value = false
  rejectReason.value = ''
}
</script>

<template>
  <div class="approval-card">
    <div class="approval-header">
      <div class="approval-icon">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M10 2L2 6V10C2 14.4 5.6 18.5 10 19.5C14.4 18.5 18 14.4 18 10V6L10 2Z" stroke="var(--warning)" stroke-width="1.5" stroke-linejoin="round"/>
          <path d="M10 7V11M10 13.5V14" stroke="var(--warning)" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
      <div>
        <div class="approval-title">승인 대기중</div>
        <div class="approval-subtitle">에이전트가 도구를 실행하려 합니다</div>
      </div>
    </div>

    <!-- Interrupt description -->
    <div v-if="description" class="approval-description">
      {{ description }}
    </div>

    <!-- Tool call tabs if multiple -->
    <div v-if="toolCalls.length > 1" class="tool-tabs">
      <button
        v-for="(tc, i) in toolCalls"
        :key="tc.id"
        class="tool-tab"
        :class="{ active: i === activeToolIndex }"
        @click="activeToolIndex = i"
      >
        {{ tc.name }}
      </button>
    </div>

    <!-- Tool call details -->
    <div v-if="activeTool" class="tool-detail">
      <div class="tool-name-row">
        <span class="tool-label">Tool</span>
        <span class="tool-name">{{ activeTool.name }}</span>
      </div>

      <div class="tool-args-section">
        <span class="tool-label">Arguments</span>
        <div v-if="!editMode" class="tool-args">
          <pre>{{ formattedArgs }}</pre>
        </div>
        <div v-else class="tool-args-edit">
          <textarea v-model="editedArgs" spellcheck="false" />
        </div>
      </div>
    </div>

    <!-- Action buttons -->
    <div class="approval-actions">
      <template v-if="!showRejectInput && !editMode">
        <button class="action-btn approve" @click="approve">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 8.5L6.5 12L13 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          승인
        </button>
        <button class="action-btn edit" @click="startEdit">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M11 2L14 5L5 14H2V11L11 2Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
          </svg>
          수정
        </button>
        <button class="action-btn reject" @click="reject">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          거부
        </button>
      </template>

      <!-- Reject reason input -->
      <template v-if="showRejectInput">
        <div class="reject-input-group">
          <input
            v-model="rejectReason"
            placeholder="거부 사유를 입력하세요 (선택)"
            @keydown.enter="reject"
          />
          <div class="reject-btns">
            <button class="action-btn reject small" @click="reject">거부 확인</button>
            <button class="action-btn cancel small" @click="cancelReject">취소</button>
          </div>
        </div>
      </template>

      <!-- Edit mode -->
      <template v-if="editMode">
        <button class="action-btn approve" @click="submitEdit">수정 승인</button>
        <button class="action-btn cancel" @click="cancelEdit">취소</button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.approval-card {
  background: var(--bg-surface);
  border: 1px solid rgba(255, 178, 36, 0.25);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  animation: fadeInUp 0.4s var(--ease-out) both;
  box-shadow: 0 0 40px rgba(255, 178, 36, 0.06);
}

.approval-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.approval-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--warning-glow);
  border-radius: var(--radius-md);
  flex-shrink: 0;
  animation: borderGlow 3s ease-in-out infinite;
  border: 1px solid rgba(255, 178, 36, 0.2);
}

.approval-title {
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--warning);
}

.approval-subtitle {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-top: 0.1rem;
}

/* Description */
.approval-description {
  font-size: 0.85rem;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.65rem 0.85rem;
  margin-bottom: 0.75rem;
  line-height: 1.5;
}

/* Tool tabs */
.tool-tabs {
  display: flex;
  gap: 0.35rem;
  margin-bottom: 0.75rem;
}

.tool-tab {
  padding: 0.3rem 0.7rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.tool-tab.active {
  background: var(--warning-glow);
  border-color: var(--warning-dim);
  color: var(--warning);
}

/* Tool detail */
.tool-detail {
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 1rem;
  margin-bottom: 1rem;
}

.tool-name-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border);
}

.tool-label {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 500;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.tool-name {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--accent);
}

.tool-args-section {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.tool-args pre {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

.tool-args-edit textarea {
  width: 100%;
  min-height: 100px;
  padding: 0.6rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-accent);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 0.78rem;
  line-height: 1.6;
  resize: vertical;
  outline: none;
}

.tool-args-edit textarea:focus {
  border-color: var(--accent);
}

/* Actions */
.approval-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.55rem 1.1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s var(--ease-out);
  background: transparent;
}

.action-btn.small {
  padding: 0.4rem 0.8rem;
  font-size: 0.78rem;
}

.action-btn.approve {
  background: var(--success);
  color: var(--text-inverse);
  border-color: var(--success);
}

.action-btn.approve:hover {
  box-shadow: 0 4px 16px var(--success-glow);
  transform: translateY(-1px);
}

.action-btn.edit {
  background: var(--warning-glow);
  color: var(--warning);
  border-color: rgba(255, 178, 36, 0.3);
}

.action-btn.edit:hover {
  background: rgba(255, 178, 36, 0.2);
}

.action-btn.reject {
  background: var(--danger-glow);
  color: var(--danger);
  border-color: rgba(255, 77, 106, 0.3);
}

.action-btn.reject:hover {
  background: rgba(255, 77, 106, 0.2);
}

.action-btn.cancel {
  color: var(--text-secondary);
}

.action-btn.cancel:hover {
  background: var(--bg-hover);
}

/* Reject input */
.reject-input-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
}

.reject-input-group input {
  width: 100%;
  padding: 0.55rem 0.85rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-family: var(--font-display);
  font-size: 0.82rem;
  outline: none;
}

.reject-input-group input:focus {
  border-color: var(--danger);
}

.reject-btns {
  display: flex;
  gap: 0.4rem;
}
</style>
