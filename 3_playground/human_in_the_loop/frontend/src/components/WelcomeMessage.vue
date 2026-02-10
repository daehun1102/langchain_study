<script setup>
const emit = defineEmits(['send'])
</script>

<template>
  <div class="welcome-msg">
    <div class="welcome-icon">
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
        <rect x="6" y="6" width="36" height="36" rx="8" stroke="var(--accent)" stroke-width="1" opacity="0.3"/>
        <rect x="12" y="12" width="24" height="24" rx="5" stroke="var(--accent)" stroke-width="1" opacity="0.5"/>
        <circle cx="24" cy="24" r="5" stroke="var(--accent)" stroke-width="1.5"/>
        <circle cx="24" cy="24" r="1.5" fill="var(--accent)"/>
      </svg>
    </div>
    <h3>반도체 공정 QC 에이전트</h3>
    <p>LOT ID를 입력하면 공정 이력 조회 및 품질 검사를 시작합니다.</p>
    <div class="welcome-chips">
      <button class="chip" @click="emit('send', 'LOT-2024001 품질 검사 요청')">LOT-2024001 검사</button>
      <button class="chip" @click="emit('send', '안녕하세요, 어떤 기능이 있나요?')">기능 안내</button>
      <button class="chip" @click="emit('send', 'LOT-2024015 Photo 공정 이상 확인')">Photo 이상 확인</button>
    </div>
  </div>
</template>

<style scoped>
.welcome-msg {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 3rem 1rem 2rem;
  animation: fadeInUp 0.6s var(--ease-out) both;
}

.welcome-icon {
  margin-bottom: 0.25rem;
}

.welcome-msg h3 {
  font-size: 1.3rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.welcome-msg p {
  font-size: 0.88rem;
  color: var(--text-secondary);
  text-align: center;
}

.welcome-chips {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 0.75rem;
}

.chip {
  padding: 0.5rem 1rem;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 100px;
  color: var(--text-secondary);
  font-family: var(--font-display);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s var(--ease-out);
}

.chip:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-glow);
  transform: translateY(-1px);
}
</style>
