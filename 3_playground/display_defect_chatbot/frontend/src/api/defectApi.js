// display_defect_chatbot/frontend/src/api/defectApi.js
const BASE = '/api'

export async function analyzeDefect({ sessionId, company, defectDescription }) {
  const res = await fetch(`${BASE}/chat/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId, company, defectDescription })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function investigateDefect({ sessionId, company, defectDescription, productId, selectedHypothesis }) {
  const res = await fetch(`${BASE}/chat/investigate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId, company, defectDescription, productId, selectedHypothesis })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getBgStatus(taskId) {
  const res = await fetch(`${BASE}/sessions/bg-status/${taskId}`)
  return res.json()
}

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
