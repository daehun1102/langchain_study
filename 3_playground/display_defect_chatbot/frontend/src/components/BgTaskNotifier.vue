<template>
  <div v-if="status === 'COMPLETED'" class="notifier">
    ✅ 장기이력 분석 완료! 결과가 분석 패널에 표시되었습니다.
  </div>
  <div v-else-if="status === 'FAILED'" class="notifier error">
    ❌ 장기이력 분석 실패
  </div>
</template>

<script setup>
defineProps(['status', 'resultText'])
</script>

<style scoped>
.notifier {
  position: fixed; bottom: 24px; right: 24px;
  background: #065f46; color: #6ee7b7; padding: 12px 20px;
  border-radius: 8px; font-size: 0.9rem; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.notifier.error { background: #7f1d1d; color: #fca5a5; }
</style>
