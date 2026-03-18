<template>
  <div class="app">
    <div class="body">
      <LeftPanel
        :sessions="sessions"
        :activeSessionId="activeSessionId"
        @new-analysis="newAnalysis"
        @load-session="loadSession"
        @delete-session="deleteSession"
        @update-title="({ id, title }) => updateSessionTitle(id, title)"
      />

      <main class="right-panel">
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

        <template v-if="step === 'result'">
          <div class="result-header">
            <div class="hypothesis-badge">선택된 가설: {{ selectedHypothesis }}</div>
            <button class="btn-reset" @click="newAnalysis">새 분석 시작</button>
          </div>
          <ChatStream :messages="chatMessages" />
          <ChatInputBar
            :mode="{ type: 'text', placeholder: '결과에 대해 추가 질문을 입력하세요… (Enter로 전송)' }"
            :disabled="isChatBlocked || loading"
            @submit="val => { userInput.value = val; sendUserMessage() }"
          />
        </template>
      </main>
    </div>
  </div>
</template>

<script setup>
import { useDefectChat } from './composables/useDefectChat.js'
import LeftPanel from './components/LeftPanel.vue'
import InputView from './components/InputView.vue'
import HypothesisSelector from './components/HypothesisSelector.vue'
import AgentSelector from './components/AgentSelector.vue'
import ChatStream from './components/ChatStream.vue'
import ChatInputBar from './components/ChatInputBar.vue'

const {
  step, loading, error, form, hypotheses, selectedHypothesis,
  chatMessages,
  sessions, activeSessionId,
  enabledAgents,
  isChatBlocked,
  startAnalysis, selectHypothesis, goBackToHypotheses, runAgents, toggleAgent,
  newAnalysis, loadSession, deleteSession, updateSessionTitle,
  userInput, sendUserMessage,
} = useDefectChat()
</script>

<style scoped>
.app { display: flex; flex-direction: column; flex: 1; overflow: hidden; }

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
</style>
