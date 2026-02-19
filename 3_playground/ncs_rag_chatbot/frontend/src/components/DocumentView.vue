<script setup>
import { ref, computed, onMounted } from 'vue'
import { fetchDocuments, uploadDocument, deleteDocument } from '../api/ncsApi.js'

const props = defineProps({
  categories: {
    type: Object,
    default: () => ({}),
  },
})

// ── 상태 ─────────────────────────────────────────────────────
const documents = ref([])
const isLoading = ref(false)
const isUploading = ref(false)
const uploadError = ref('')
const uploadSuccess = ref('')

// 업로드 폼 상태
const selectedFile = ref(null)
const fileInputRef = ref(null)
const selectedMainCategory = ref('')
const selectedSubCategory = ref('')

// ── 계산 속성 ─────────────────────────────────────────────────
const mainCategories = computed(() => Object.keys(props.categories))
const subCategories = computed(() => {
  if (!selectedMainCategory.value) return []
  return props.categories[selectedMainCategory.value] || []
})

// ── 수명주기 ─────────────────────────────────────────────────
onMounted(loadDocuments)

// ── 메서드 ───────────────────────────────────────────────────
async function loadDocuments() {
  isLoading.value = true
  try {
    documents.value = await fetchDocuments()
  } catch (e) {
    console.error('문서 목록 조회 실패:', e)
  } finally {
    isLoading.value = false
  }
}

function onFileChange(e) {
  selectedFile.value = e.target.files[0] || null
  uploadError.value = ''
  uploadSuccess.value = ''
}

function onMainCategoryChange() {
  selectedSubCategory.value = ''
}

async function handleUpload() {
  if (!selectedFile.value) {
    uploadError.value = '파일을 선택해주세요.'
    return
  }
  uploadError.value = ''
  uploadSuccess.value = ''
  isUploading.value = true
  try {
    const doc = await uploadDocument(
      selectedFile.value,
      selectedMainCategory.value || null,
      selectedSubCategory.value || null,
    )
    uploadSuccess.value = `"${doc.filename}" 등록 완료 (상태: ${statusLabel(doc.status)})`
    // 폼 초기화
    selectedFile.value = null
    selectedMainCategory.value = ''
    selectedSubCategory.value = ''
    if (fileInputRef.value) fileInputRef.value.value = ''
    await loadDocuments()
  } catch (e) {
    uploadError.value = '업로드에 실패했습니다. 서버 상태를 확인해주세요.'
  } finally {
    isUploading.value = false
  }
}

async function handleDelete(docId, filename) {
  if (!confirm(`"${filename}" 문서를 삭제하시겠습니까?\nOracle과 벡터 데이터가 모두 삭제됩니다.`)) return
  try {
    await deleteDocument(docId)
    documents.value = documents.value.filter((d) => d.docId !== docId)
  } catch (e) {
    alert('삭제에 실패했습니다.')
  }
}

function statusLabel(status) {
  const labels = { INDEXED: '인덱싱 완료', PENDING: '처리 중', FAILED: '실패' }
  return labels[status] || status
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('ko-KR')
}
</script>

<template>
  <div class="doc-view">
    <!-- 업로드 섹션 -->
    <section class="upload-section">
      <h2 class="section-title">PDF 문서 등록</h2>
      <div class="upload-form">
        <label class="file-label">
          <input
            ref="fileInputRef"
            type="file"
            accept=".pdf"
            class="file-input"
            @change="onFileChange"
          />
          <span class="file-name">{{ selectedFile ? selectedFile.name : '파일 선택 (.pdf)' }}</span>
        </label>

        <select
          v-model="selectedMainCategory"
          class="cat-select"
          @change="onMainCategoryChange"
        >
          <option value="">메인 카테고리 선택</option>
          <option v-for="cat in mainCategories" :key="cat" :value="cat">{{ cat }}</option>
        </select>

        <select
          v-model="selectedSubCategory"
          class="cat-select"
          :disabled="!selectedMainCategory"
        >
          <option value="">서브 카테고리 선택</option>
          <option v-for="sub in subCategories" :key="sub" :value="sub">{{ sub }}</option>
        </select>

        <button class="upload-btn" :disabled="isUploading" @click="handleUpload">
          {{ isUploading ? '등록 중...' : '등록' }}
        </button>
      </div>

      <p v-if="uploadError" class="msg-error">{{ uploadError }}</p>
      <p v-if="uploadSuccess" class="msg-success">{{ uploadSuccess }}</p>
    </section>

    <!-- 문서 목록 섹션 -->
    <section class="list-section">
      <div class="list-header">
        <h2 class="section-title">등록된 문서 목록</h2>
        <button class="refresh-btn" :disabled="isLoading" @click="loadDocuments">
          ↺ 새로고침
        </button>
      </div>

      <div v-if="isLoading" class="state-msg">로딩 중...</div>
      <div v-else-if="documents.length === 0" class="state-msg">등록된 문서가 없습니다.</div>
      <table v-else class="doc-table">
        <thead>
          <tr>
            <th>파일명</th>
            <th>메인 카테고리</th>
            <th>서브 카테고리</th>
            <th>등록일</th>
            <th>상태</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in documents" :key="doc.docId">
            <td class="col-filename">{{ doc.filename }}</td>
            <td>{{ doc.mainCategory || '-' }}</td>
            <td>{{ doc.subCategory || '-' }}</td>
            <td>{{ formatDate(doc.uploadDate) }}</td>
            <td>
              <span :class="['status-badge', doc.status?.toLowerCase()]">
                {{ statusLabel(doc.status) }}
              </span>
            </td>
            <td>
              <button class="del-btn" @click="handleDelete(doc.docId, doc.filename)">삭제</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<style scoped>
.doc-view {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  padding: 2rem;
  height: 100%;
  overflow-y: auto;
  color: var(--text-primary, #e2e8f0);
}

/* ── 섹션 공통 ── */
.section-title {
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent, #00e5c8);
  margin-bottom: 1rem;
}

/* ── 업로드 폼 ── */
.upload-section {
  background: var(--bg-secondary, rgba(255,255,255,0.04));
  border: 1px solid var(--border, rgba(255,255,255,0.08));
  border-radius: 8px;
  padding: 1.5rem;
}

.upload-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}

.file-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(0,229,200,0.05);
  border: 1px solid var(--border, rgba(255,255,255,0.12));
  border-radius: 6px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  transition: border-color 0.2s;
  min-width: 220px;
}
.file-label:hover { border-color: var(--accent, #00e5c8); }

.file-input {
  display: none;
}

.file-name {
  font-size: 0.85rem;
  color: var(--text-secondary, #94a3b8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.cat-select {
  background: var(--bg-secondary, #1e293b);
  border: 1px solid var(--border, rgba(255,255,255,0.12));
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  color: var(--text-primary, #e2e8f0);
  font-size: 0.85rem;
  cursor: pointer;
}
.cat-select:disabled { opacity: 0.4; cursor: not-allowed; }
.cat-select:focus { outline: 1px solid var(--accent, #00e5c8); }

.upload-btn {
  background: var(--accent, #00e5c8);
  color: #0f172a;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1.5rem;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  transition: opacity 0.2s;
}
.upload-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.upload-btn:hover:not(:disabled) { opacity: 0.85; }

.msg-error { color: #f87171; font-size: 0.85rem; margin-top: 0.5rem; }
.msg-success { color: #4ade80; font-size: 0.85rem; margin-top: 0.5rem; }

/* ── 문서 목록 ── */
.list-section {
  flex: 1;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.refresh-btn {
  background: transparent;
  border: 1px solid var(--border, rgba(255,255,255,0.12));
  border-radius: 6px;
  color: var(--text-secondary, #94a3b8);
  padding: 0.35rem 0.85rem;
  font-size: 0.8rem;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}
.refresh-btn:hover:not(:disabled) {
  border-color: var(--accent, #00e5c8);
  color: var(--accent, #00e5c8);
}
.refresh-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.state-msg {
  color: var(--text-secondary, #94a3b8);
  font-size: 0.9rem;
  padding: 2rem 0;
  text-align: center;
}

.doc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.doc-table th {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid var(--border, rgba(255,255,255,0.08));
  color: var(--text-secondary, #94a3b8);
  font-weight: 500;
  letter-spacing: 0.04em;
}
.doc-table td {
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  color: var(--text-primary, #e2e8f0);
  vertical-align: middle;
}
.doc-table tr:hover td { background: rgba(255,255,255,0.03); }

.col-filename {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 상태 배지 ── */
.status-badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.status-badge.indexed { background: rgba(74,222,128,0.15); color: #4ade80; }
.status-badge.pending { background: rgba(250,204,21,0.15); color: #facc15; }
.status-badge.failed  { background: rgba(248,113,113,0.15); color: #f87171; }

/* ── 삭제 버튼 ── */
.del-btn {
  background: transparent;
  border: 1px solid rgba(248,113,113,0.4);
  border-radius: 4px;
  color: #f87171;
  padding: 0.25rem 0.65rem;
  font-size: 0.75rem;
  cursor: pointer;
  transition: background 0.2s;
}
.del-btn:hover { background: rgba(248,113,113,0.1); }
</style>
