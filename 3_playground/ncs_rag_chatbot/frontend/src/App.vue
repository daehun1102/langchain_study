<script setup>
import { ref, onMounted } from 'vue'
import FilterPanel from './components/FilterPanel.vue'
import ChatView from './components/ChatView.vue'
import DocumentView from './components/DocumentView.vue'
import { healthCheck, fetchCategories } from './api/ncsApi.js'

const isConnected = ref(false)
const sidebarOpen = ref(true)
const categories = ref({})
const activeTab = ref('chat')   // 'chat' | 'documents'

onMounted(async () => {
  isConnected.value = await healthCheck()
  if (isConnected.value) {
    try {
      categories.value = await fetchCategories()
    } catch {
      categories.value = {}
    }
  }
})

const activeFilter = ref({ mainCategory: null, subCategory: null })

function onFilterChange(mainCat, subCat) {
  activeFilter.value = { mainCategory: mainCat, subCategory: subCat }
}

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}
</script>

<template>
  <div class="app-shell">
    <div class="bg-grid" />
    <div class="bg-glow" />

    <!-- 상단 탭 바 -->
    <nav class="tab-bar">
      <button
        :class="['tab-btn', { active: activeTab === 'chat' }]"
        @click="activeTab = 'chat'"
      >
        대화
      </button>
      <button
        :class="['tab-btn', { active: activeTab === 'documents' }]"
        @click="activeTab = 'documents'"
      >
        문서 관리
      </button>
    </nav>

    <!-- 탭 콘텐츠 -->
    <div class="tab-content">
      <!-- 대화 탭 -->
      <template v-if="activeTab === 'chat'">
        <FilterPanel
          :categories="categories"
          :activeFilter="activeFilter"
          :isConnected="isConnected"
          :isOpen="sidebarOpen"
          @filter-change="onFilterChange"
          @toggle="toggleSidebar"
        />
        <main class="main-area">
          <ChatView
            :isConnected="isConnected"
            :activeFilter="activeFilter"
          />
        </main>
      </template>

      <!-- 문서 관리 탭 -->
      <template v-else-if="activeTab === 'documents'">
        <main class="main-area full-width">
          <DocumentView :categories="categories" />
        </main>
      </template>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  position: relative;
  overflow: hidden;
}

.bg-grid {
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 229, 200, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 229, 200, 0.03) 1px, transparent 1px);
  background-size: 48px 48px;
  pointer-events: none;
  z-index: 0;
}

.bg-glow {
  position: fixed;
  top: -30%;
  right: -10%;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(0, 229, 200, 0.06) 0%, transparent 70%);
  pointer-events: none;
  z-index: 0;
}

/* ── 탭 바 ── */
.tab-bar {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 0 1.5rem;
  height: 44px;
  background: var(--bg-primary, #0f172a);
  border-bottom: 1px solid rgba(255,255,255,0.08);
  position: relative;
  z-index: 10;
  flex-shrink: 0;
}

.tab-btn {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary, #94a3b8);
  font-size: 0.85rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  padding: 0 1.25rem;
  height: 100%;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}
.tab-btn:hover { color: var(--text-primary, #e2e8f0); }
.tab-btn.active {
  color: var(--accent, #00e5c8);
  border-bottom-color: var(--accent, #00e5c8);
}

/* ── 탭 콘텐츠 ── */
.tab-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
  z-index: 1;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.main-area.full-width {
  width: 100%;
}
</style>
