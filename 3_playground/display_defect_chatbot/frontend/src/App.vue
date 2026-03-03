<template>
  <div class="app">
    <header class="header">
      <h1>🔬 Display Defect Analyzer</h1>
      <span class="subtitle">삼성 디스플레이 픽셀 불량 분석 AI</span>
      <button v-if="step !== 'input'" @click="reset" class="btn-reset">새 분석 시작</button>
    </header>

    <main class="main">
      <InputView v-if="step === 'input'" :form="form" :loading="loading" :error="error" @analyze="analyze" />
      <HypothesisSelector v-if="step === 'hypotheses'" :hypotheses="hypotheses" :loading="loading" @select="investigate" />
      <div v-if="step === 'investigating'" class="investigating">
        <div class="spinner"></div>
        <p>병렬 분석 중... 공정이력, 반송이력, 테스트결과를 동시에 조회하고 있습니다.</p>
      </div>
      <AgentResultPanel v-if="step === 'result'" :result="result" :hypothesis="selectedHypothesis" />
    </main>

    <BgTaskNotifier v-if="result.longTermTaskId" :status="result.longTermStatus" :result-text="result.longTermResult" />
  </div>
</template>

<script setup>
import { useDefectChat } from './composables/useDefectChat.js'
import InputView from './components/InputView.vue'
import HypothesisSelector from './components/HypothesisSelector.vue'
import AgentResultPanel from './components/AgentResultPanel.vue'
import BgTaskNotifier from './components/BgTaskNotifier.vue'

const { step, loading, error, form, hypotheses, selectedHypothesis, result, analyze, investigate, reset } = useDefectChat()
</script>

<style>
.app { display: flex; flex-direction: column; min-height: 100vh; }
.header { background: #1a1d27; padding: 16px 24px; display: flex; align-items: center; gap: 16px; border-bottom: 1px solid #2a2d3a; }
.header h1 { font-size: 1.3rem; color: #60a5fa; }
.subtitle { color: #6b7280; font-size: 0.85rem; }
.btn-reset { margin-left: auto; background: #374151; color: #e0e0e0; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; }
.main { flex: 1; padding: 24px; max-width: 1200px; margin: 0 auto; width: 100%; }
.investigating { text-align: center; padding: 60px; color: #9ca3af; }
.spinner { width: 40px; height: 40px; border: 3px solid #374151; border-top-color: #60a5fa; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 16px; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
