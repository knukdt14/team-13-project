import { API_BASE, request, queryString } from './client'

export const PATHS = Object.freeze({
  meta: '/meta',
  policies: '/policies',
  regions: '/regions/summary',
  provinces: '/geo/provinces',
  ask: '/ask',
  askStream: '/ask/stream',
  documents: '/documents',
  sessions: '/sessions',
})

export const getMeta = () => request(PATHS.meta)
export const getPolicies = (conditions, extra = {}) =>
  request(`${PATHS.policies}?${queryString({ ...conditions, ...extra })}`)
export const getRegionSummary = (conditions) => {
  const { region: _region, include_nationwide: _nationwide, ...rest } = conditions
  return request(`${PATHS.regions}?${queryString(rest)}`)
}
export const getProvinces = () => request(PATHS.provinces)
export const ask = (body) => request(PATHS.ask, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
})
export const streamUrl = (values) => `${API_BASE}${PATHS.askStream}?${queryString(values)}`
export const getMessages = (sessionId) =>
  request(`${PATHS.sessions}/${sessionId}/messages`)

export async function uploadDocuments(sessionId, files) {
  const form = new FormData()
  form.append('session_id', sessionId)
  for (const file of files) form.append('files', file)
  return request(PATHS.documents, { method: 'POST', body: form })
}
export const getDocuments = (sessionId) =>
  request(`${PATHS.documents}?${queryString({ session_id: sessionId })}`)
export const deleteDocument = (sessionId, docId) =>
  request(`${PATHS.documents}/${docId}?${queryString({ session_id: sessionId })}`, { method: 'DELETE' })
