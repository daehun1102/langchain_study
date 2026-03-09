// frontend/src/api/defectApi.js
const BASE = '/api'

export async function callAgent(payload) {
  const res = await fetch(`${BASE}/chat/agent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getBgStatus(taskId) {
  const res = await fetch(`${BASE}/chat/bg-status/${taskId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// 문서 관리 (유지)
export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/documents`, { method: 'POST', body: form })
  return res.json()
}

export async function fetchDocuments() {
  const res = await fetch(`${BASE}/documents`)
  return res.json()
}

export async function deleteDocument(docId) {
  await fetch(`${BASE}/documents/${docId}`, { method: 'DELETE' })
}
