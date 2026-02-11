<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatView from './components/ChatView.vue'
import { client } from './api/langgraph.js'

const THREADS_STORAGE_KEY = 'fab_threads'

const threads = ref([])
const activeThreadId = ref(null)
const isConnected = ref(false)
const sidebarOpen = ref(true)

function saveThreads() {
  localStorage.setItem(THREADS_STORAGE_KEY, JSON.stringify(threads.value))
}

function loadThreads() {
  const saved = localStorage.getItem(THREADS_STORAGE_KEY)
  if (saved) {
    try {
      threads.value = JSON.parse(saved)
    } catch {
      threads.value = []
    }
  }
}

function handleTitleUpdate(e) {
  const { threadId, title } = e.detail
  const thread = threads.value.find(t => t.id === threadId)
  if (thread) {
    thread.title = title
    saveThreads()
  }
}

onMounted(async () => {
  loadThreads()
  isConnected.value = await client.healthCheck()
  window.addEventListener('thread-title-update', handleTitleUpdate)
})

onUnmounted(() => {
  window.removeEventListener('thread-title-update', handleTitleUpdate)
})

watch(threads, saveThreads, { deep: true })

async function createNewThread() {
  try {
    const thread = await client.createThread()
    threads.value.unshift({
      id: thread.thread_id,
      title: `Thread ${threads.value.length + 1}`,
      createdAt: new Date().toISOString(),
    })
    activeThreadId.value = thread.thread_id
  } catch {
    // 서버 미연결 시 로컬 mock thread
    const mockId = `local-${Date.now()}`
    threads.value.unshift({
      id: mockId,
      title: `Thread ${threads.value.length + 1}`,
      createdAt: new Date().toISOString(),
    })
    activeThreadId.value = mockId
  }
}

function selectThread(id) {
  activeThreadId.value = id
}

function deleteThread(id) {
  threads.value = threads.value.filter(t => t.id !== id)
  localStorage.removeItem(`thread_messages_${id}`)
  if (activeThreadId.value === id) {
    activeThreadId.value = threads.value.length > 0 ? threads.value[0].id : null
  }
}

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}
</script>

<template>
  <div class="app-layout">
    <!-- Background grid effect -->
    <div class="bg-grid" />
    <div class="bg-glow" />

    <Sidebar
      :threads="threads"
      :activeThreadId="activeThreadId"
      :isConnected="isConnected"
      :isOpen="sidebarOpen"
      @new-thread="createNewThread"
      @select-thread="selectThread"
      @delete-thread="deleteThread"
      @toggle="toggleSidebar"
    />

    <main class="main-area" :class="{ 'sidebar-collapsed': !sidebarOpen }">
      <ChatView
        v-if="activeThreadId"
        :threadId="activeThreadId"
        :isConnected="isConnected"
        :key="activeThreadId"
      />

      <!-- Empty state -->
      <div v-else class="empty-state">
        <div class="empty-state-content">
          <div class="empty-logo">
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
              <rect x="4" y="4" width="56" height="56" rx="12" stroke="var(--accent)" stroke-width="1.5" opacity="0.3"/>
              <rect x="12" y="12" width="40" height="40" rx="8" stroke="var(--accent)" stroke-width="1.5" opacity="0.6"/>
              <circle cx="32" cy="32" r="8" stroke="var(--accent)" stroke-width="2"/>
              <line x1="32" y1="20" x2="32" y2="24" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round"/>
              <line x1="32" y1="40" x2="32" y2="44" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round"/>
              <line x1="20" y1="32" x2="24" y2="32" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round"/>
              <line x1="40" y1="32" x2="44" y2="32" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </div>
          <h1 class="empty-title">FAB Control</h1>
          <p class="empty-subtitle">Human-in-the-Loop Agent Interface</p>
          <p class="empty-desc">
            반도체 공정 품질 관리를 위한 AI 에이전트와 대화하세요.<br/>
            에이전트의 도구 호출을 승인, 수정, 거부할 수 있습니다.
          </p>
          <button class="btn-primary" @click="createNewThread">
            <span class="btn-icon">+</span>
            새 대화 시작
          </button>
          <div class="status-badge" :class="isConnected ? 'connected' : 'disconnected'">
            <span class="status-dot" />
            {{ isConnected ? 'Agent 서버 연결됨' : 'Agent 서버 미연결 — 데모 모드' }}
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  width: 100%;
  height: 100vh;
  position: relative;
  overflow: hidden;
}

/* Background effects */
.bg-grid {
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 229, 200, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 229, 200, 0.03) 1px, transparent 1px);
  background-size: 48px 48px;
  pointer-events: none;
  z-index: 0;
}

.bg-glow {
  position: fixed;
  top: -30%;
  right: -10%;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(0, 229, 200, 0.06) 0%, transparent 70%);
  pointer-events: none;
  z-index: 0;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
  min-width: 0;
  transition: margin-left 0.4s var(--ease-out);
}

/* Empty state */
.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.empty-state-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  animation: fadeInUp 0.8s var(--ease-out) both;
}

.empty-logo {
  margin-bottom: 0.5rem;
  animation: fadeIn 1s ease both 0.2s;
}

.empty-title {
  font-family: var(--font-display);
  font-size: 2.8rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  line-height: 1;
}

.empty-subtitle {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 400;
  color: var(--accent);
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.empty-desc {
  font-size: 0.95rem;
  color: var(--text-secondary);
  text-align: center;
  line-height: 1.7;
  max-width: 420px;
  margin-top: 0.5rem;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.85rem 2rem;
  background: var(--accent);
  color: var(--text-inverse);
  border: none;
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s var(--ease-out);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(0, 229, 200, 0.3);
}

.btn-primary:active {
  transform: translateY(0);
}

.btn-icon {
  font-size: 1.3rem;
  line-height: 1;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1.5rem;
  padding: 0.45rem 1rem;
  border-radius: 100px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.02em;
}

.status-badge.connected {
  background: var(--success-glow);
  color: var(--success);
  border: 1px solid rgba(0, 214, 143, 0.2);
}

.status-badge.disconnected {
  background: var(--warning-glow);
  color: var(--warning);
  border: 1px solid rgba(255, 178, 36, 0.2);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s ease-in-out infinite;
}
</style>
