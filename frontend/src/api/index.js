const BASE = "/api"

// Global refresh-funksjon settes av AuthProvider
let _refresh = null
export function setRefreshFn(fn) { _refresh = fn }

export async function apiFetch(path, options = {}, token = null) {
  const headers = { "Content-Type": "application/json", ...options.headers }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
    credentials: "include", // send cookies alltid
  })

  // Automatisk refresh ved 401
  if (res.status === 401 && _refresh) {
    const newToken = await _refresh()
    if (newToken) {
      // Retry med nytt token
      headers["Authorization"] = `Bearer ${newToken}`
      const retry = await fetch(`${BASE}${path}`, {
        ...options,
        headers,
        credentials: "include",
      })
      if (!retry.ok) {
        const err = await retry.json().catch(() => ({ detail: retry.statusText }))
        throw new Error(err.detail || err.message || "Feil")
      }
      return retry.json()
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || err.message || "Feil")
  }

  return res.json()
}
