<template>
  <div class="hypothesis-view">
    <div class="view-header">
      <span class="tag-mono">// HYPOTHESIS.GENERATED</span>
      <h2>원인 가설 선택</h2>
      <p class="subtitle">AI가 과거 사례를 기반으로 생성한 가설입니다. 가장 적합한 것을 선택하세요.</p>
    </div>

    <div class="hypotheses">
      <button
        v-for="(h, i) in hypotheses"
        :key="i"
        class="hypothesis-card"
        :disabled="loading"
        :style="{ '--delay': `${i * 0.07}s` }"
        @click="$emit('select', h)"
      >
        <span class="hyp-num">{{ String(i + 1).padStart(2, '0') }}</span>
        <span class="hyp-text">{{ h }}</span>
        <svg class="hyp-arrow" viewBox="0 0 16 16" fill="none" width="15" height="15">
          <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps(['hypotheses', 'loading'])
defineEmits(['select'])
</script>

<style scoped>
.hypothesis-view {
  max-width: 680px;
  margin: 0 auto;
  animation: fadeUp 0.3s ease;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

.view-header { margin-bottom: 24px; }

.tag-mono {
  display: inline-block;
  font-family: var(--mono);
  font-size: 0.68rem;
  color: var(--ac-cyan);
  letter-spacing: 0.1em;
  margin-bottom: 8px;
  opacity: 0.75;
}

h2 {
  font-family: var(--sans);
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--text-1);
  margin-bottom: 5px;
}

.subtitle {
  font-size: 0.78rem;
  color: var(--text-3);
  line-height: 1.5;
}

.hypotheses {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.hypothesis-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-left: 2px solid var(--border);
  border-radius: 8px;
  padding: 13px 16px;
  color: var(--text-1);
  text-align: left;
  cursor: pointer;
  font-family: var(--sans);
  font-size: 0.87rem;
  line-height: 1.65;
  transition: border-color 0.17s, background 0.17s, transform 0.15s;
  animation: slideIn 0.3s ease both;
  animation-delay: var(--delay, 0s);
  width: 100%;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(-8px); }
  to   { opacity: 1; transform: translateX(0); }
}

.hypothesis-card:hover:not(:disabled) {
  border-color: var(--ac-cyan);
  border-left-color: var(--ac-cyan);
  background: rgba(0, 200, 255, 0.03);
  transform: translateX(3px);
}

.hypothesis-card:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.hyp-num {
  font-family: var(--mono);
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--ac-cyan);
  opacity: 0.65;
  margin-top: 3px;
  flex-shrink: 0;
  letter-spacing: 0.04em;
}

.hyp-text { flex: 1; }

.hyp-arrow {
  color: var(--ac-cyan);
  opacity: 0;
  transition: opacity 0.17s, transform 0.17s;
  flex-shrink: 0;
  margin-top: 3px;
}

.hypothesis-card:hover .hyp-arrow {
  opacity: 0.65;
  transform: translateX(3px);
}
</style>
