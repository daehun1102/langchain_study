<template>
  <div class="typing-indicator">
    <div class="typing-avatar">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <rect x="2" y="2" width="14" height="14" rx="3" stroke="var(--accent)" stroke-width="1.2"/>
        <circle cx="9" cy="9" r="2.5" fill="var(--accent)"/>
      </svg>
    </div>
    <div class="typing-dots">
      <span /><span /><span />
    </div>
    <span class="typing-text">문서 검색 및 답변 생성 중...</span>
  </div>
</template>

<style scoped>
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.5rem 0;
  animation: fadeIn 0.3s ease both;
}

.typing-avatar {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-glow);
  border: 1px solid var(--border-accent);
  border-radius: var(--radius-sm);
}

.typing-dots {
  display: flex;
  gap: 3px;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.2s ease-in-out infinite;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.15s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.3s;
}

.typing-text {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--text-tertiary);
}
</style>
