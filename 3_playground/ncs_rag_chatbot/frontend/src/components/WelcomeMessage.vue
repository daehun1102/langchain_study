<script setup>
const emit = defineEmits(['send'])
</script>

<template>
  <div class="welcome-msg">
    <div class="welcome-icon">
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
        <rect x="6" y="6" width="36" height="36" rx="8" stroke="var(--accent)" stroke-width="1" opacity="0.3"/>
        <rect x="12" y="12" width="24" height="24" rx="5" stroke="var(--accent)" stroke-width="1" opacity="0.5"/>
        <path d="M19 19h10M19 24h7M19 29h8" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
    </div>
    <h3>NCS 문서 검색 에이전트</h3>
    <p>
      국가직무능력표준 문서에서 필요한 정보를 검색합니다.<br/>
      왼쪽 패널에서 카테고리를 선택하면 필터링된 검색이 가능합니다.
    </p>
    <div class="welcome-chips">
      <button class="chip" @click="emit('send', 'SW아키텍쳐에서 품질 속성이란 무엇인가요?')">SW아키텍쳐 품질 속성</button>
      <button class="chip" @click="emit('send', '테스트 기획의 핵심 절차를 설명해주세요')">테스트 기획 절차</button>
      <button class="chip" @click="emit('send', '요구사항 확인 방법에 대해 알려주세요')">요구사항 확인</button>
      <button class="chip" @click="emit('send', '문제해결능력의 핵심 요소는 무엇인가요?')">문제해결능력</button>
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
  line-height: 1.7;
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
