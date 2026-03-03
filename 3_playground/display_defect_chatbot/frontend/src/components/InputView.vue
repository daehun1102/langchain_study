<template>
  <div class="input-view">
    <h2>불량 정보 입력</h2>
    <div class="form">
      <label>보고 회사</label>
      <input v-model="form.company" placeholder="예: A사" />
      <label>불량 증상 설명</label>
      <textarea v-model="form.defectDescription" rows="4"
        placeholder="예: 화면 좌측 상단 픽셀 10개가 완전히 꺼져 있음 (Dead Pixel)"></textarea>
      <label>제품 ID / Lot No</label>
      <input v-model="form.productId" placeholder="예: LOT-A001" />
      <button @click="$emit('analyze')" :disabled="loading || !form.defectDescription">
        {{ loading ? '분석 중...' : '원인 분석 시작' }}
      </button>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps(['form', 'loading', 'error'])
defineEmits(['analyze'])
</script>

<style scoped>
.input-view { max-width: 600px; margin: 40px auto; }
h2 { color: #60a5fa; margin-bottom: 24px; }
.form { display: flex; flex-direction: column; gap: 12px; }
label { color: #9ca3af; font-size: 0.85rem; }
input, textarea { background: #1e2130; border: 1px solid #374151; border-radius: 8px; padding: 10px 14px; color: #e0e0e0; font-size: 0.95rem; width: 100%; }
button { background: #2563eb; color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-size: 1rem; margin-top: 8px; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
.error { color: #f87171; font-size: 0.85rem; }
</style>
