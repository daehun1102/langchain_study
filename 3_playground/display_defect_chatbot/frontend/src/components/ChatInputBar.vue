<template>
  <div class="chat-input-bar">

    <!-- type='text': 기존 입력바 그대로 -->
    <template v-if="mode.type === 'text'">
      <div v-if="disabled" class="chat-blocked-notice">
        ⏳ 장기 이력 분석 완료 후 채팅이 가능합니다
      </div>
      <template v-else>
        <textarea
          v-model="textValue"
          class="chat-input"
          :placeholder="mode.placeholder || '입력하세요…'"
          rows="1"
          :disabled="disabled"
          @keydown.enter.exact.prevent="submitText"
          @input="autoResize"
          ref="textareaEl"
        ></textarea>
        <button
          class="chat-send-btn"
          :disabled="disabled || !textValue.trim()"
          @click="submitText"
          title="전송"
        >
          <svg viewBox="0 0 16 16" fill="none" width="15" height="15">
            <path d="M14 8L2 2l3 6-3 6 12-6z" fill="currentColor"/>
          </svg>
        </button>
      </template>
    </template>

    <!-- type='single': 가설 선택 버튼 목록 -->
    <template v-else-if="mode.type === 'single'">
      <div class="single-options">
        <button
          v-for="(opt, i) in mode.options"
          :key="i"
          class="option-btn"
          :disabled="disabled"
          @click="$emit('submit', opt)"
        >
          {{ opt.text }}
        </button>
      </div>
    </template>

    <!-- type='multi': 에이전트 체크박스 + 실행 버튼 -->
    <template v-else-if="mode.type === 'multi'">
      <div class="multi-options">
        <label
          v-for="opt in mode.options"
          :key="opt.key"
          class="multi-item"
        >
          <input
            type="checkbox"
            v-model="localEnabled[opt.key]"
            :disabled="disabled"
          />
          <span>{{ opt.icon }} {{ opt.label }}</span>
        </label>
        <button
          class="run-btn"
          :disabled="disabled || selectedKeys.length === 0"
          @click="submitMulti"
        >
          분석 실행
        </button>
      </div>
    </template>

  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'

const props = defineProps({
  mode: {
    type: Object,
    default: () => ({ type: 'text', placeholder: '' }),
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['submit'])

// --- type='text' ---
const textValue = ref('')
const textareaEl = ref(null)

function submitText() {
  const val = textValue.value.trim()
  if (!val) return
  textValue.value = ''
  if (textareaEl.value) {
    textareaEl.value.style.height = 'auto'
  }
  emit('submit', val)
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

// --- type='multi' ---
// mode.options가 바뀔 때마다 enabledAgents 스냅샷으로 localEnabled 초기화
const localEnabled = reactive({})

watch(
  () => props.mode,
  (newMode) => {
    if (newMode.type === 'multi') {
      Object.keys(localEnabled).forEach(k => delete localEnabled[k])
      const initial = newMode.enabledAgents || {}
      newMode.options?.forEach(opt => {
        localEnabled[opt.key] = initial[opt.key] ?? true
      })
    }
  },
  { immediate: true }
)

const selectedKeys = computed(() =>
  Object.keys(localEnabled).filter(k => localEnabled[k])
)

function submitMulti() {
  emit('submit', [...selectedKeys.value])
}
</script>

<style scoped>
.chat-input-bar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 16px 12px;
  border-top: 1px solid #2a2d3a;
  background: #13161f;
  flex-shrink: 0;
}

.chat-input {
  flex: 1;
  background: #1a1d27;
  border: 1px solid #2a2d3a;
  border-radius: 8px;
  padding: 9px 13px;
  color: #e0e0e0;
  font-family: 'Segoe UI', sans-serif;
  font-size: 0.86rem;
  resize: none;
  outline: none;
  line-height: 1.5;
  min-height: 38px;
  max-height: 120px;
  overflow-y: auto;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.chat-input:focus {
  border-color: #00c8ff;
  box-shadow: 0 0 0 3px rgba(0, 200, 255, 0.07);
}
.chat-input::placeholder { color: #3d4a5c; }
.chat-input:disabled { opacity: 0.5; cursor: not-allowed; }

.chat-send-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: #00c8ff;
  color: #060b12;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.18s, box-shadow 0.18s, opacity 0.18s;
}
.chat-send-btn:hover:not(:disabled) {
  background: #2dd4f0;
  box-shadow: 0 0 16px rgba(0, 200, 255, 0.3);
}
.chat-send-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.chat-blocked-notice {
  flex: 1;
  text-align: center;
  color: #6b7280;
  font-size: 0.82rem;
  padding: 10px 0;
  font-style: italic;
}

/* type='single' */
.single-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
  padding: 4px 0;
}

.option-btn {
  background: rgba(59, 130, 246, 0.07);
  border: 1px solid rgba(59, 130, 246, 0.28);
  border-radius: 7px;
  padding: 8px 14px;
  color: #93c5fd;
  font-size: 0.82rem;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  line-height: 1.45;
  text-align: left;
}
.option-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.5);
}
.option-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* type='multi' */
.multi-options {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  flex: 1;
  padding: 4px 0;
}

.multi-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 0.83rem;
  color: var(--text-2, #94a3b8);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #2a2d3a;
  border-radius: 7px;
  padding: 6px 12px;
  transition: border-color 0.15s;
  user-select: none;
}
.multi-item:hover { border-color: #3b4a5c; }
.multi-item input[type="checkbox"] {
  accent-color: #3b82f6;
  cursor: pointer;
}

.run-btn {
  background: #1d4ed8;
  color: #fff;
  border: none;
  border-radius: 7px;
  padding: 8px 20px;
  font-size: 0.84rem;
  cursor: pointer;
  transition: background 0.18s, opacity 0.18s;
  font-weight: 600;
  white-space: nowrap;
}
.run-btn:hover:not(:disabled) { background: #2563eb; }
.run-btn:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
