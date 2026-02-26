<script setup>
import FeedbackChatPanel from './FeedbackChatPanel.vue'
</script>

<template>
  <div class="feedback-view">
    <header class="feedback-header">
      <h2>NCS 과제 피드백 비교</h2>
      <p>좌: Subagent (v1) &nbsp;|&nbsp; 우: HandOff (v2)</p>
    </header>

    <div class="panels">
      <FeedbackChatPanel version="v1" label="Subagent (v1)" />
      <div class="divider" />
      <FeedbackChatPanel version="v2" label="HandOff (v2)" />
    </div>
  </div>
</template>

<style scoped>
.feedback-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.feedback-header {
  padding: 0.6rem 1.5rem;
  border-bottom: 1px solid var(--border, rgba(255,255,255,0.08));
  flex-shrink: 0;
}

.feedback-header h2 {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary, #e2e8f0);
  margin: 0 0 0.1rem;
}

.feedback-header p {
  font-size: 0.72rem;
  color: var(--text-secondary, #94a3b8);
  margin: 0;
}

.panels {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

.divider {
  width: 1px;
  background: var(--border, rgba(255,255,255,0.08));
  flex-shrink: 0;
}
</style>
