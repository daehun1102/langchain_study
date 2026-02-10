<script setup>
import { computed } from 'vue'

const props = defineProps({
  threads: Array,
  activeThreadId: String,
  isConnected: Boolean,
  isOpen: Boolean,
})

const emit = defineEmits(['new-thread', 'select-thread', 'toggle'])

const formattedThreads = computed(() =>
  props.threads.map(t => ({
    ...t,
    time: new Date(t.createdAt).toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    }),
  }))
)
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: !isOpen }">
    <div class="sidebar-inner">
      <!-- Header -->
      <div class="sidebar-header">
        <div class="brand" v-show="isOpen">
          <div class="brand-icon">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect x="2" y="2" width="16" height="16" rx="3" stroke="var(--accent)" stroke-width="1.5"/>
              <circle cx="10" cy="10" r="3" fill="var(--accent)"/>
            </svg>
          </div>
          <div>
            <div class="brand-name">FAB Control</div>
            <div class="brand-tag">v0.1</div>
          </div>
        </div>
        <button class="toggle-btn" @click="emit('toggle')" :title="isOpen ? '사이드바 닫기' : '사이드바 열기'">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path
              :d="isOpen
                ? 'M11 4L6 9L11 14'
                : 'M7 4L12 9L7 14'"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
      </div>

      <!-- New thread -->
      <button class="new-thread-btn" @click="emit('new-thread')" v-show="isOpen">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 3V13M3 8H13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        새 대화
      </button>

      <!-- Thread list -->
      <div class="thread-list" v-show="isOpen">
        <div class="thread-section-label">대화 목록</div>
        <div
          v-for="thread in formattedThreads"
          :key="thread.id"
          class="thread-item"
          :class="{ active: thread.id === activeThreadId }"
          @click="emit('select-thread', thread.id)"
        >
          <svg class="thread-icon" width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 4h10M2 7h7M2 10h5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
          <div class="thread-info">
            <span class="thread-title">{{ thread.title }}</span>
            <span class="thread-time">{{ thread.time }}</span>
          </div>
        </div>

        <div v-if="!threads.length" class="thread-empty">
          아직 대화가 없습니다
        </div>
      </div>

      <!-- Footer -->
      <div class="sidebar-footer" v-show="isOpen">
        <div class="conn-status" :class="isConnected ? 'on' : 'off'">
          <span class="conn-dot" />
          {{ isConnected ? '연결됨' : '미연결' }}
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 280px;
  min-width: 280px;
  height: 100vh;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 10;
  transition: all 0.4s var(--ease-out);
}

.sidebar.collapsed {
  width: 56px;
  min-width: 56px;
}

.sidebar-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Header */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid var(--border);
  min-height: 60px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.brand-icon {
  flex-shrink: 0;
}

.brand-name {
  font-weight: 700;
  font-size: 0.95rem;
  letter-spacing: -0.02em;
}

.brand-tag {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  color: var(--text-tertiary);
  letter-spacing: 0.05em;
}

.toggle-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.toggle-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
  border-color: var(--border-accent);
}

/* New thread button */
.new-thread-btn {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin: 0.75rem;
  padding: 0.65rem 1rem;
  background: transparent;
  border: 1px dashed var(--border);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s var(--ease-out);
}

.new-thread-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-glow);
}

/* Thread list */
.thread-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 0.5rem;
}

.thread-section-label {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 500;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  padding: 0.75rem 0.5rem 0.4rem;
}

.thread-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 0.75rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
  margin-bottom: 2px;
}

.thread-item:hover {
  background: var(--bg-hover);
}

.thread-item.active {
  background: var(--accent-glow);
  border-left: 2px solid var(--accent);
}

.thread-item.active .thread-title {
  color: var(--accent);
}

.thread-icon {
  flex-shrink: 0;
  color: var(--text-tertiary);
}

.thread-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.thread-title {
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.thread-time {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--text-tertiary);
}

.thread-empty {
  padding: 2rem 1rem;
  text-align: center;
  font-size: 0.8rem;
  color: var(--text-tertiary);
}

/* Footer */
.sidebar-footer {
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--border);
}

.conn-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--text-tertiary);
}

.conn-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.conn-status.on .conn-dot {
  background: var(--success);
  box-shadow: 0 0 8px var(--success);
}

.conn-status.off .conn-dot {
  background: var(--text-tertiary);
}
</style>
