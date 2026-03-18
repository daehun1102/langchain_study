<!-- src/components/TabPlaceholder.vue -->
<template>
  <div class="placeholder-wrap">
    <div class="placeholder-box">
      <div class="placeholder-icon">🚧</div>
      <h2 class="placeholder-title">{{ label }}</h2>
      <p class="placeholder-sub">준비 중입니다</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
})
</script>

<style scoped>
.placeholder-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.placeholder-box {
  text-align: center;
  color: #4b5563;
}
.placeholder-icon { font-size: 3rem; margin-bottom: 16px; }
.placeholder-title { font-size: 1.4rem; color: #6b7280; margin-bottom: 8px; }
.placeholder-sub { font-size: 0.9rem; color: #374151; }
</style>
