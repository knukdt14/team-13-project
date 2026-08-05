import { useCallback, useState } from 'react'

const STORAGE_KEY = 'youth-policy-conditions'
export const EMPTY_CONDITIONS = {
  age: '', employment: '', education: '', region: '',
  include_closed: false, include_nationwide: false,
}

function restore() {
  try { return { ...EMPTY_CONDITIONS, ...JSON.parse(localStorage.getItem(STORAGE_KEY)) } }
  catch { return EMPTY_CONDITIONS }
}

export default function useConditions() {
  const [conditions, setConditions] = useState(restore)
  const update = useCallback((patch) => setConditions((current) => {
    const next = { ...current, ...patch }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    return next
  }), [])
  const reset = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setConditions(EMPTY_CONDITIONS)
  }, [])
  return { conditions, update, reset }
}
