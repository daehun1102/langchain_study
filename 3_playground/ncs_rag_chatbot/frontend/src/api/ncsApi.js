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
  if (mainCategory) body.main_category = mainCategory
  if (subCategory) body.sub_category = subCategory

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
