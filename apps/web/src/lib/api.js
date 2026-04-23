import { clearToken, getToken } from './auth'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function getJson(path, init = {}) {
  const token = getToken()
  const headers = { ...(init.headers || {}) }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const response = await fetch(`${API_URL}${path}`, { ...init, headers })

  if (response.status === 401) {
    clearToken()
    window.location.reload()
    return
  }

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }

  return response.json()
}
