<template>
  <div class="app">
    <!-- 헤더 -->
    <header class="header">
      <h1>🔬 Display Defect Analyzer</h1>
      <span class="subtitle">삼성 디스플레이 픽셀 불량 분석 AI</span>
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
            @analyze="analyze"
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
            @run-all="runAllEnabled"
          />
        </div>

        <!-- result 단계: 가설 배지 + ChatStream -->
        <template v-if="step === 'result'">
          <div class="result-header">
            <div class="hypothesis-badge">선택된 가설: {{ selectedHypothesis }}</div>
            <button class="btn-reset" @click="newAnalysis">새 분석 시작</button>
          </div>
          <ChatStream :messages="chatMessages" />
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

const {
  step, loading, error, form, hypotheses, selectedHypothesis,
  enabledAgents, chatMessages,
  sessions, activeSessionId,
  analyze, selectHypothesis, toggleAgent, runAllEnabled,
  newAnalysis, loadSession, deleteSession,
} = useDefectChat()
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0f1117; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
</style>

<style scoped>
.app { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }

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
  flex-shrink: 0;
  max-height: 60vh;
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
