<template>
  <div class="app">
    <div class="body">
      <LeftPanel
        :sessions="sessions"
        :activeSessionId="activeSessionId"
        @new-analysis="newAnalysis"
        @load-session="loadSession"
        @delete-session="deleteSession"
        @update-title="({ id, title }) => updateSessionTitle(id, title)"
      />

      <main class="right-panel">
        <ChatStream
          :messages="chatMessages"
          @select-hypothesis="h => handleSubmit(h)"
          @run-agents="msg => handleSubmit(
            Object.keys(msg.enabledAgents).filter(k => msg.enabledAgents[k])
          )"
        />
        <ChatInputBar
          :mode="inputMode"
          :disabled="loading"
          @submit="handleSubmit"
        />
      </main>
    </div>
  </div>
</template>

<script setup>
import { useChatbotFlow } from './composables/useChatbotFlow.js'
import LeftPanel from './components/LeftPanel.vue'
import ChatStream from './components/ChatStream.vue'
import ChatInputBar from './components/ChatInputBar.vue'

const {
  chatMessages, inputMode, loading,
  sessions, activeSessionId,
  newAnalysis, loadSession, deleteSession, updateSessionTitle,
  handleSubmit,
} = useChatbotFlow()
</script>

<style scoped>
.app { display: flex; flex-direction: column; flex: 1; overflow: hidden; }

.body { display: flex; flex: 1; overflow: hidden; }

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
