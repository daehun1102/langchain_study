<template>
  <div class="hypothesis-view">
    <h2>원인 가설 선택</h2>
    <p class="hint">AI가 과거 사례를 기반으로 생성한 가설입니다. 가장 적합한 것을 선택하세요.</p>
    <div class="hypotheses">
      <button
        v-for="(h, i) in hypotheses"
        :key="i"
        class="hypothesis-btn"
        :disabled="loading"
        @click="$emit('select', h)"
      >
        {{ h }}
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps(['hypotheses', 'loading'])
defineEmits(['select'])
</script>

<style scoped>
.hypothesis-view { max-width: 700px; margin: 40px auto; }
h2 { color: #60a5fa; margin-bottom: 8px; }
.hint { color: #6b7280; font-size: 0.85rem; margin-bottom: 24px; }
.hypotheses { display: flex; flex-direction: column; gap: 12px; }
.hypothesis-btn {
  background: #1e2130; border: 1px solid #3b4fd0; border-radius: 10px;
  padding: 16px 20px; color: #e0e0e0; text-align: left; cursor: pointer; font-size: 0.95rem;
  transition: background 0.2s;
}
.hypothesis-btn:hover { background: #2a305a; border-color: #60a5fa; }
</style>
