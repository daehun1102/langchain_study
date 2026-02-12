<script setup>
import { ref, onMounted } from 'vue'
import FilterPanel from './components/FilterPanel.vue'
import ChatView from './components/ChatView.vue'
import { healthCheck, fetchCategories } from './api/ncsApi.js'

const isConnected = ref(false)
const sidebarOpen = ref(true)
const categories = ref({})

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
  <div class="app-layout">
    <div class="bg-grid" />
    <div class="bg-glow" />

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
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
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

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
  min-width: 0;
  transition: margin-left 0.4s var(--ease-out);
}
</style>
