<template>
  <div class="input-view">
    <div class="view-header">
      <span class="tag-mono">// DEFECT.INIT</span>
      <h2>불량 정보 입력</h2>
      <p class="subtitle">분석 대상 정보를 입력하면 AI가 원인 가설을 생성합니다</p>
    </div>

    <div class="form">
      <div class="field">
        <label>
          <span class="field-num">01</span>
          <span>보고 회사</span>
        </label>
        <input v-model="form.company" placeholder="SDC" autocomplete="off" spellcheck="false" />
      </div>

      <div class="field">
        <label>
          <span class="field-num">02</span>
          <span>불량 증상 설명</span>
        </label>
        <textarea
          v-model="form.defectDescription"
          rows="4"
          placeholder="예: 화면 좌측 상단 픽셀 10개가 완전히 꺼져 있음 (Dead Pixel)"
          spellcheck="false"
        ></textarea>
      </div>

      <div class="field">
        <label>
          <span class="field-num">03</span>
          <span>제품 ID / Lot No</span>
        </label>
        <input v-model="form.productId" placeholder="LOT-A001" autocomplete="off" spellcheck="false" />
      </div>

      <button
        @click="$emit('analyze')"
        :disabled="loading || !form.defectDescription"
        class="analyze-btn"
      >
        <span v-if="loading" class="btn-spinner"></span>
        <svg v-else class="btn-icon" viewBox="0 0 16 16" fill="none" width="16" height="16">
          <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ loading ? '원인 분석 중...' : '원인 분석 시작' }}
      </button>

      <p v-if="error" class="error-msg">
        <span class="error-badge">!</span>
        {{ error }}
      </p>
    </div>
  </div>
</template>

<script setup>
defineProps(['form', 'loading', 'error'])
defineEmits(['analyze'])
</script>

<style scoped>
.input-view {
  max-width: 560px;
  margin: 0 auto;
  animation: fadeUp 0.3s ease;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

.view-header { margin-bottom: 28px; }

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
  letter-spacing: -0.01em;
}

.subtitle {
  font-size: 0.78rem;
  color: var(--text-3);
  line-height: 1.5;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--text-2);
  letter-spacing: 0.02em;
}

.field-num {
  font-family: var(--mono);
  font-size: 0.62rem;
  color: var(--ac-cyan);
  background: rgba(0, 200, 255, 0.08);
  border: 1px solid rgba(0, 200, 255, 0.18);
  border-radius: 3px;
  padding: 1px 5px;
  letter-spacing: 0.04em;
}

input, textarea {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 14px;
  color: var(--text-1);
  font-family: var(--sans);
  font-size: 0.88rem;
  width: 100%;
  transition: border-color 0.2s, box-shadow 0.2s;
  outline: none;
  resize: none;
}

input:focus, textarea:focus {
  border-color: var(--ac-cyan);
  box-shadow: 0 0 0 3px rgba(0, 200, 255, 0.07);
}

input::placeholder, textarea::placeholder {
  color: var(--text-3);
  font-size: 0.84rem;
}

.analyze-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  background: var(--ac-cyan);
  color: #060b12;
  border: none;
  padding: 12px 20px;
  border-radius: 7px;
  cursor: pointer;
  font-family: var(--sans);
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  margin-top: 4px;
  transition: background 0.18s, box-shadow 0.18s, opacity 0.18s;
}

.analyze-btn:hover:not(:disabled) {
  background: #2dd4f0;
  box-shadow: 0 0 22px rgba(0, 200, 255, 0.28);
}

.analyze-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-icon { flex-shrink: 0; }

.btn-spinner {
  width: 13px;
  height: 13px;
  border: 2px solid rgba(6, 11, 18, 0.25);
  border-top-color: #060b12;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
  flex-shrink: 0;
}

@keyframes spin { to { transform: rotate(360deg); } }

.error-msg {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--ac-red);
  font-size: 0.8rem;
  background: rgba(248, 113, 113, 0.05);
  border: 1px solid rgba(248, 113, 113, 0.18);
  border-radius: 6px;
  padding: 8px 12px;
  line-height: 1.5;
}

.error-badge {
  width: 17px;
  height: 17px;
  border-radius: 50%;
  border: 1.5px solid var(--ac-red);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.68rem;
  font-weight: 700;
  flex-shrink: 0;
}
</style>
