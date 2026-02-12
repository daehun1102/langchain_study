<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  loading: Boolean,
})

const emit = defineEmits(['send'])

const message = ref('')
const textarea = ref(null)

function send() {
  const text = message.value.trim()
  if (!text || props.loading) return
  emit('send', text)
  message.value = ''
  if (textarea.value) {
    textarea.value.style.height = 'auto'
  }
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function autoResize() {
  const el = textarea.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}

watch(message, () => {
  requestAnimationFrame(autoResize)
})
</script>

<template>
  <div class="chat-input-wrapper">
    <div class="input-container" :class="{ disabled: loading }">
      <div class="input-glow" />
      <textarea
        ref="textarea"
        v-model="message"
        @keydown="onKeydown"
        :disabled="loading"
        placeholder="NCS 문서에 대해 질문하세요... (예: SW아키텍쳐에서 품질 속성이란?)"
        rows="1"
      />
      <button
        class="send-btn"
        :disabled="!message.trim() || loading"
        @click="send"
      >
        <svg v-if="!loading" width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M3 9H15M10 4L15 9L10 14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <div v-else class="send-spinner" />
      </button>
    </div>
    <div class="input-hint">
      <span class="key-badge">Enter</span> 전송 &nbsp;·&nbsp;
      <span class="key-badge">Shift+Enter</span> 줄바꿈
    </div>
  </div>
</template>

<style scoped>
.chat-input-wrapper {
  padding: 0 1.5rem 1.25rem;
  animation: fadeInUp 0.5s var(--ease-out) both;
}

.input-container {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  padding: 0.6rem 0.6rem 0.6rem 1rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: 14px;
  position: relative;
  transition: all 0.3s var(--ease-out);
}

.input-container:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-glow), 0 8px 32px rgba(0, 0, 0, 0.3);
}

.input-container.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.input-glow {
  position: absolute;
  inset: -1px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--accent-glow), transparent, var(--accent-glow));
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
  z-index: -1;
}

.input-container:focus-within .input-glow {
  opacity: 1;
}

textarea {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-family: var(--font-display);
  font-size: 0.9rem;
  line-height: 1.5;
  resize: none;
  max-height: 200px;
  padding: 0.3rem 0;
}

textarea::placeholder {
  color: var(--text-tertiary);
}

.send-btn {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 10px;
  background: var(--accent);
  color: var(--text-inverse);
  cursor: pointer;
  transition: all 0.2s var(--ease-out);
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 16px rgba(0, 229, 200, 0.35);
}

.send-btn:active:not(:disabled) {
  transform: scale(0.95);
}

.send-btn:disabled {
  background: var(--bg-hover);
  color: var(--text-tertiary);
  cursor: not-allowed;
}

.send-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.input-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  margin-top: 0.5rem;
  font-size: 0.68rem;
  color: var(--text-tertiary);
}

.key-badge {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.6rem;
}
</style>
