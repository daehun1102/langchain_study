<!-- src/RootApp.vue -->
<template>
  <div class="root-app">
    <header class="header">
      <h1>🔬 Display Defect Analyzer</h1>
      <span class="subtitle">삼성 디스플레이 픽셀 불량 분석 AI</span>
      <div class="email-setting">
        <label for="notify-email" class="email-label">📧 알림 이메일</label>
        <input
          id="notify-email"
          v-model="userEmail"
          type="email"
          class="email-input"
          placeholder="완료 알림 받을 이메일"
          @keydown.enter="saveEmail"
        />
        <button class="email-save-btn" @click="saveEmail" :class="{ saved: emailSaved }">
          {{ emailSaved ? '✓ 저장됨' : '저장' }}
        </button>
      </div>
    </header>

    <nav class="tab-bar">
      <button
        v-for="tab in TABS"
        :key="tab.id"
        class="tab"
        :class="{ active: activeTab.id === tab.id }"
        @click="switchTab(tab)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <keep-alive>
      <component
        :is="activeTab.component"
        :key="activeTab.id"
        :label="activeTab.label"
      />
    </keep-alive>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUserEmail } from './composables/useUserEmail.js'
import App from './App.vue'
import ChatbotApp from './ChatbotApp.vue'
import TabPlaceholder from './components/TabPlaceholder.vue'

const TABS = [
  { id: 'analysis',    label: '단계별 분석', component: App },
  { id: 'chatbot',     label: '챗봇',        component: ChatbotApp },
  { id: 'rag-test',    label: 'RAG TEST',    component: TabPlaceholder },
  { id: 'milvus-test', label: 'Milvus TEST', component: TabPlaceholder },
]

// Active tab — persisted to localStorage, falls back to first tab
const stored = localStorage.getItem('active_tab')
const initialTab = TABS.find(t => t.id === stored) ?? TABS[0]
const activeTab = ref(initialTab)

function switchTab(tab) {
  activeTab.value = tab
  try { localStorage.setItem('active_tab', tab.id) } catch (_) {}
}

// Email setting (singleton ref from useUserEmail; watcher handles localStorage)
const { userEmail } = useUserEmail()
const savedEmailValue = ref(localStorage.getItem('user_email') || '')
const emailSaved = computed(() => !!userEmail.value && userEmail.value === savedEmailValue.value)

function saveEmail() {
  // Only update visual state — useUserEmail's watcher persists to localStorage
  savedEmailValue.value = userEmail.value
}
</script>

<style>
/* Global reset — applied once here, removed from App.vue and ChatbotApp.vue */
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0f1117; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
</style>

<style scoped>
.root-app {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.header {
  background: #1a1d27;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 1px solid #2a2d3a;
  flex-shrink: 0;
}
.header h1 { font-size: 1.2rem; color: #60a5fa; }
.subtitle { color: #6b7280; font-size: 0.85rem; }

.tab-bar {
  background: #13151f;
  display: flex;
  gap: 0;
  border-bottom: 1px solid #2a2d3a;
  flex-shrink: 0;
  padding: 0 8px;
}

.tab {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: #6b7280;
  cursor: pointer;
  font-size: 0.85rem;
  padding: 8px 16px;
  margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
}
.tab:hover { color: #9ca3af; }
.tab.active {
  color: #60a5fa;
  border-bottom-color: #3b82f6;
}

.email-setting {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}
.email-label { color: #6b7280; font-size: 0.78rem; white-space: nowrap; }
.email-input {
  background: #1a1d27;
  border: 1px solid #2a2d3a;
  border-radius: 6px;
  padding: 5px 10px;
  color: #e0e0e0;
  font-size: 0.78rem;
  width: 200px;
  outline: none;
}
.email-input:focus { border-color: #00c8ff; }
.email-input::placeholder { color: #374151; }
.email-save-btn {
  background: #1e293b;
  color: #94a3b8;
  border: 1px solid #2a2d3a;
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 0.75rem;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.18s, color 0.18s, border-color 0.18s;
}
.email-save-btn:hover { background: #2a3a52; color: #e0e0e0; border-color: #3b4a5c; }
.email-save-btn.saved { background: rgba(16, 185, 129, 0.12); color: #4ade80; border-color: rgba(16, 185, 129, 0.3); }
</style>
