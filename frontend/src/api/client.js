import * as mock from './mock'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const USE_MOCK = String(import.meta.env.VITE_USE_MOCK).toLowerCase() === 'true'

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function request(path, options = {}) {
  if (USE_MOCK) return mock.respond(path, options)
  const response = await fetch(`${API_BASE}${path}`, options)
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(payload?.detail || `요청에 실패했어요 (${response.status})`, response.status)
  }
  return response.json()
}

export function queryString(values = {}) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(values)) {
    if (value === '' || value == null || value === false) continue
    if (Array.isArray(value)) value.forEach((item) => query.append(key, item))
    else query.set(key, String(value))
  }
  return query.toString()
}

export { API_BASE, USE_MOCK }
