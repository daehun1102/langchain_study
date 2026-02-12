<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  categories: Object,
  activeFilter: Object,
  isConnected: Boolean,
  isOpen: Boolean,
})

const emit = defineEmits(['filter-change', 'toggle'])

const expandedCategories = ref({})

function toggleCategory(mainCat) {
  expandedCategories.value[mainCat] = !expandedCategories.value[mainCat]
}

function isCategoryExpanded(mainCat) {
  return expandedCategories.value[mainCat] !== false
}

function selectFilter(mainCat, subCat) {
  // Toggle off if same filter is clicked again
  if (
    props.activeFilter.mainCategory === mainCat &&
    props.activeFilter.subCategory === subCat
  ) {
    emit('filter-change', null, null)
  } else {
    emit('filter-change', mainCat, subCat)
  }
}

function selectMainCategory(mainCat) {
  if (props.activeFilter.mainCategory === mainCat && !props.activeFilter.subCategory) {
    emit('filter-change', null, null)
  } else {
    emit('filter-change', mainCat, null)
  }
}

function clearFilter() {
  emit('filter-change', null, null)
}

const hasActiveFilter = computed(() => {
  return props.activeFilter.mainCategory || props.activeFilter.subCategory
})

const categoryEntries = computed(() => Object.entries(props.categories || {}))
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: !isOpen }">
    <div class="sidebar-inner">
      <!-- Header -->
      <div class="sidebar-header">
        <div class="brand" v-show="isOpen">
          <div class="brand-icon">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect x="2" y="2" width="16" height="16" rx="3" stroke="var(--accent)" stroke-width="1.5"/>
              <path d="M7 7h6M7 10h4M7 13h5" stroke="var(--accent)" stroke-width="1.2" stroke-linecap="round"/>
            </svg>
          </div>
          <div>
            <div class="brand-name">NCS Archive</div>
            <div class="brand-tag">v0.1</div>
          </div>
        </div>
        <button class="toggle-btn" @click="emit('toggle')" :title="isOpen ? '패널 닫기' : '패널 열기'">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path
              :d="isOpen ? 'M11 4L6 9L11 14' : 'M7 4L12 9L7 14'"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
      </div>

      <!-- Filter section -->
      <div class="filter-section" v-show="isOpen">
        <div class="section-label">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M1 2h12L8 7.5V11l-2 1V7.5L1 2z" stroke="currentColor" stroke-width="1.1" stroke-linejoin="round"/>
          </svg>
          메타데이터 필터
        </div>

        <!-- Clear filter button -->
        <button
          v-if="hasActiveFilter"
          class="clear-filter-btn"
          @click="clearFilter"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M3 3L9 9M9 3L3 9" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
          </svg>
          필터 해제
        </button>

        <!-- Category tree -->
        <div class="category-tree">
          <div
            v-for="[mainCat, subCats] in categoryEntries"
            :key="mainCat"
            class="category-group"
          >
            <!-- Main category -->
            <div
              class="category-main"
              :class="{
                active: activeFilter.mainCategory === mainCat && !activeFilter.subCategory,
                'has-active-child': activeFilter.mainCategory === mainCat && activeFilter.subCategory,
              }"
              @click="selectMainCategory(mainCat)"
            >
              <button
                class="expand-btn"
                @click.stop="toggleCategory(mainCat)"
              >
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                  <path
                    :d="isCategoryExpanded(mainCat) ? 'M2 3.5L5 6.5L8 3.5' : 'M3.5 2L6.5 5L3.5 8'"
                    stroke="currentColor"
                    stroke-width="1.3"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </button>
              <span class="cat-label">{{ mainCat }}</span>
              <span class="cat-count">{{ subCats.length }}</span>
            </div>

            <!-- Sub categories -->
            <div class="sub-list" v-show="isCategoryExpanded(mainCat)">
              <div
                v-for="subCat in subCats"
                :key="subCat"
                class="category-sub"
                :class="{ active: activeFilter.mainCategory === mainCat && activeFilter.subCategory === subCat }"
                @click="selectFilter(mainCat, subCat)"
              >
                <span class="sub-dot" />
                <span class="sub-label">{{ subCat }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Active filter indicator -->
      <div class="active-filter-display" v-show="isOpen && hasActiveFilter">
        <div class="filter-tag">
          <span class="filter-tag-label">활성 필터</span>
          <span class="filter-tag-value">
            {{ activeFilter.mainCategory }}
            <template v-if="activeFilter.subCategory"> › {{ activeFilter.subCategory }}</template>
          </span>
        </div>
      </div>

      <!-- Footer -->
      <div class="sidebar-footer" v-show="isOpen">
        <div class="conn-status" :class="isConnected ? 'on' : 'off'">
          <span class="conn-dot" />
          {{ isConnected ? '서버 연결됨' : '서버 미연결' }}
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 280px;
  min-width: 280px;
  height: 100vh;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 10;
  transition: all 0.4s var(--ease-out);
}

.sidebar.collapsed {
  width: 56px;
  min-width: 56px;
}

.sidebar-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Header */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid var(--border);
  min-height: 60px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.brand-icon { flex-shrink: 0; }

.brand-name {
  font-weight: 700;
  font-size: 0.95rem;
  letter-spacing: -0.02em;
}

.brand-tag {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  color: var(--text-tertiary);
  letter-spacing: 0.05em;
}

.toggle-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.toggle-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
  border-color: var(--border-accent);
}

/* Filter section */
.filter-section {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 500;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  padding: 0 0.25rem 0.6rem;
}

.clear-filter-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  width: 100%;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.5rem;
  background: var(--danger-glow);
  border: 1px solid rgba(255, 77, 106, 0.2);
  border-radius: var(--radius-sm);
  color: var(--danger);
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.clear-filter-btn:hover {
  background: rgba(255, 77, 106, 0.2);
  border-color: var(--danger);
}

/* Category tree */
.category-tree {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.category-group {
  margin-bottom: 0.25rem;
}

.category-main {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.55rem 0.5rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 0.82rem;
  font-weight: 600;
}

.category-main:hover {
  background: var(--bg-hover);
}

.category-main.active {
  background: var(--accent-glow);
  color: var(--accent);
}

.category-main.has-active-child .cat-label {
  color: var(--accent-dim);
}

.expand-btn {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.expand-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.cat-label {
  flex: 1;
  color: var(--text-primary);
}

.cat-count {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  color: var(--text-tertiary);
  background: var(--bg-tertiary);
  padding: 0.1rem 0.4rem;
  border-radius: 100px;
}

/* Sub categories */
.sub-list {
  padding-left: 1.6rem;
}

.category-sub {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.5rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.category-sub:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.category-sub.active {
  background: var(--accent-glow);
  color: var(--accent);
}

.category-sub.active .sub-dot {
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent);
}

.sub-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--text-tertiary);
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.sub-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Active filter display */
.active-filter-display {
  padding: 0.75rem;
  border-top: 1px solid var(--border);
}

.filter-tag {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.6rem 0.75rem;
  background: var(--accent-glow);
  border: 1px solid var(--border-accent);
  border-radius: var(--radius-sm);
  animation: fadeIn 0.3s ease both;
}

.filter-tag-label {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  color: var(--accent-dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.filter-tag-value {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--accent);
}

/* Footer */
.sidebar-footer {
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--border);
}

.conn-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--text-tertiary);
}

.conn-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.conn-status.on .conn-dot {
  background: var(--success);
  box-shadow: 0 0 8px var(--success);
}

.conn-status.off .conn-dot {
  background: var(--text-tertiary);
}
</style>
