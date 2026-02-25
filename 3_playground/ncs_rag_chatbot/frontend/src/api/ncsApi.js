const BASE_URL = ''

export async function healthCheck() {
  try {
    const res = await fetch(`${BASE_URL}/api/health`)
    return res.ok
  } catch {
    return false
  }
}

export async function fetchCategories() {
  const res = await fetch(`${BASE_URL}/api/categories`)
  return res.json()
}

export async function sendChat(query, mainCategory = null, subCategory = null) {
  const body = { query }
  if (mainCategory) body.mainCategory = mainCategory
  if (subCategory) body.subCategory = subCategory

  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    throw new Error(`Server error: ${res.status}`)
  }

  return res.json()
}

export async function fetchDocuments() {
  const res = await fetch(`${BASE_URL}/api/documents`)
  if (!res.ok) throw new Error(`Server error: ${res.status}`)
  return res.json()
}

export async function uploadDocument(file, mainCategory, subCategory) {
  const formData = new FormData()
  formData.append('file', file)
  if (mainCategory) formData.append('mainCategory', mainCategory)
  if (subCategory) formData.append('subCategory', subCategory)

  const res = await fetch(`${BASE_URL}/api/documents`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return res.json()
}

export async function deleteDocument(docId) {
  const res = await fetch(`${BASE_URL}/api/documents/${docId}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`)
  return true
}

export async function sendFeedbackChat(query, threadId = null) {
  const body = { query }
  if (threadId) body.threadId = threadId

  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    throw new Error(`Server error: ${res.status}`)
  }

  return res.json()
}
