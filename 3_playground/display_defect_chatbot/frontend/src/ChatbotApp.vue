<template>
  <div class="app">
    <!-- 헤더 (App.vue와 동일) -->
    <header class="header">
      <h1>🔬 Display Defect Analyzer</h1>
      <span class="subtitle">삼성 디스플레이 픽셀 불량 분석 AI (챗봇 모드)</span>
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

    <div class="body">
      <!-- 왼쪽: 분석 이력 패널 (App.vue와 동일) -->
      <LeftPanel
        :sessions="sessions"
        :activeSessionId="activeSessionId"
        @new-analysis="newAnalysis"
        @load-session="loadSession"
        @delete-session="deleteSession"
        @update-title="({ id, title }) => updateSessionTitle(id, title)"
      />

      <!-- 오른쪽: 챗봇 UI — step 없이 ChatStream + ChatInputBar만 -->
      <main class="right-panel">
        <ChatStream
          :messages="chatMessages"
          @select-hypothesis="h => handleSubmit(h)"
          @run-agents="msg => handleSubmit(
            Object.keys(msg.enabledAgents).filter(k => msg.enabledAgents[k])
          )"
        />
        <ChatInputBar
          :mode="inputMode"
          :disabled="loading"
          @submit="handleSubmit"
        />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useChatbotFlow } from './composables/useChatbotFlow.js'
import LeftPanel from './components/LeftPanel.vue'
import ChatStream from './components/ChatStream.vue'
import ChatInputBar from './components/ChatInputBar.vue'

const {
  chatMessages, inputMode, loading,
  sessions, activeSessionId,
  userEmail,
  newAnalysis, loadSession, deleteSession, updateSessionTitle,
  handleSubmit,
} = useChatbotFlow()

// 이메일 저장 상태 (App.vue와 동일)
const savedEmailValue = ref(localStorage.getItem('user_email') || '')
const emailSaved = computed(() => !!userEmail.value && userEmail.value === savedEmailValue.value)

function saveEmail() {
  savedEmailValue.value = userEmail.value
  try { localStorage.setItem('user_email', userEmail.value || '') } catch (_) {}
}
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0f1117; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
</style>

<style scoped>
.app { display: flex; flex-direction: column; height: 100%; overflow: hidden; }

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

.body { display: flex; flex: 1; overflow: hidden; }

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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
