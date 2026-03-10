<template>
  <div class="app">
    <!-- 헤더 -->
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

    <div class="body">
      <!-- 왼쪽: 분석 이력 패널 -->
      <LeftPanel
        :sessions="sessions"
        :activeSessionId="activeSessionId"
        @new-analysis="newAnalysis"
        @load-session="loadSession"
        @delete-session="deleteSession"
      />

      <!-- 오른쪽: 단계별 흐름 + ChatStream -->
      <main class="right-panel">
        <!-- 단계별 흐름 영역 -->
        <div class="flow-area" :class="{ collapsed: step === 'result' }">
          <InputView
            v-if="step === 'input'"
            :form="form" :loading="loading" :error="error"
            @analyze="startAnalysis"
          />
          <HypothesisSelector
            v-if="step === 'hypotheses'"
            :hypotheses="hypotheses" :loading="loading"
            @select="selectHypothesis"
          />
          <AgentSelector
            v-if="step === 'agent_select'"
            :hypothesis="selectedHypothesis"
            :enabledAgents="enabledAgents"
            :loading="loading"
            @toggle="toggleAgent"
            @run-all="runAgents"
            @back="goBackToHypotheses"
          />
        </div>

        <!-- result 단계: 가설 배지 + ChatStream + 사용자 입력 -->
        <template v-if="step === 'result'">
          <div class="result-header">
            <div class="hypothesis-badge">선택된 가설: {{ selectedHypothesis }}</div>
            <button class="btn-reset" @click="newAnalysis">새 분석 시작</button>
          </div>
          <ChatStream :messages="chatMessages" />
          <div class="chat-input-bar">
            <div v-if="isChatBlocked" class="chat-blocked-notice">
              ⏳ 장기 이력 분석 완료 후 채팅이 가능합니다
            </div>
            <template v-else>
              <textarea
                v-model="userInput"
                class="chat-input"
                placeholder="결과에 대해 추가 질문을 입력하세요… (Enter로 전송)"
                rows="1"
                @keydown.enter.exact.prevent="sendUserMessage"
                @input="autoResize"
                ref="chatInputEl"
              ></textarea>
              <button
                class="chat-send-btn"
                :disabled="!userInput.trim() || loading"
                @click="sendUserMessage"
                title="전송"
              >
                <svg viewBox="0 0 16 16" fill="none" width="15" height="15">
                  <path d="M14 8L2 2l3 6-3 6 12-6z" fill="currentColor"/>
                </svg>
              </button>
            </template>
          </div>
        </template>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDefectChat } from './composables/useDefectChat.js'
import LeftPanel from './components/LeftPanel.vue'
import InputView from './components/InputView.vue'
import HypothesisSelector from './components/HypothesisSelector.vue'
import AgentSelector from './components/AgentSelector.vue'
import ChatStream from './components/ChatStream.vue'

const {
  step, loading, error, form, hypotheses, selectedHypothesis,
  chatMessages,
  sessions, activeSessionId,
  enabledAgents,
  isChatBlocked,
  userEmail,
  startAnalysis, selectHypothesis, goBackToHypotheses, runAgents, toggleAgent,
  newAnalysis, loadSession, deleteSession,
  userInput, sendUserMessage,
} = useDefectChat()

// 저장된 이메일과 현재 입력값 비교로 저장 상태 표시
const savedEmailValue = ref(localStorage.getItem('user_email') || '')
const emailSaved = computed(() => !!userEmail.value && userEmail.value === savedEmailValue.value)

function saveEmail() {
  savedEmailValue.value = userEmail.value
  try { localStorage.setItem('user_email', userEmail.value || '') } catch (_) {}
}


function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
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

.flow-area {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}
.flow-area.collapsed { display: none; }

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #2a2d3a;
  flex-shrink: 0;
}
.hypothesis-badge {
  background: #1e3a5f;
  border: 1px solid #3b82f6;
  border-radius: 8px;
  padding: 8px 14px;
  color: #93c5fd;
  font-size: 0.85rem;
}
.btn-reset {
  background: #374151;
  color: #e0e0e0;
  border: none;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}
.btn-reset:hover { background: #4b5563; }

.chat-input-bar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 16px 12px;
  border-top: 1px solid #2a2d3a;
  background: #13161f;
  flex-shrink: 0;
}

.chat-input {
  flex: 1;
  background: #1a1d27;
  border: 1px solid #2a2d3a;
  border-radius: 8px;
  padding: 9px 13px;
  color: #e0e0e0;
  font-family: 'Segoe UI', sans-serif;
  font-size: 0.86rem;
  resize: none;
  outline: none;
  line-height: 1.5;
  min-height: 38px;
  max-height: 120px;
  overflow-y: auto;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.chat-input:focus {
  border-color: #00c8ff;
  box-shadow: 0 0 0 3px rgba(0, 200, 255, 0.07);
}

.chat-input::placeholder { color: #3d4a5c; }

.chat-send-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: #00c8ff;
  color: #060b12;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.18s, box-shadow 0.18s, opacity 0.18s;
}

.chat-send-btn:hover:not(:disabled) {
  background: #2dd4f0;
  box-shadow: 0 0 16px rgba(0, 200, 255, 0.3);
}

.chat-send-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.chat-blocked-notice {
  flex: 1;
  text-align: center;
  color: #6b7280;
  font-size: 0.82rem;
  padding: 10px 0;
  font-style: italic;
}

.email-setting {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}
.email-label {
  color: #6b7280;
  font-size: 0.78rem;
  white-space: nowrap;
}
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
