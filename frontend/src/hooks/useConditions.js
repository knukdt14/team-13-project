import { useCallback, useMemo, useState } from 'react'

const STORAGE_KEY = 'youth-policy-conditions'
export const EMPTY_CONDITIONS = {
  age: '', employment: '', education: '', region: '',
  include_closed: false, include_nationwide: false,
}

// 실제 정책 데이터에서 뽑은 범위. 하한은 15세(60건), 상한은 49세(75건)까지 쓴다.
// 백엔드 UserProfile 도 같은 값으로 검증한다. (src/backend/schemas/profile.py)
export const YOUTH_MIN_AGE = 15
export const YOUTH_MAX_AGE = 49

export function isYouthAge(value) {
  const typed = String(value ?? '').trim()
  if (typed === '') return true          // 입력 안 함은 정상
  const number = Number(typed)
  return Number.isFinite(number) && number >= YOUTH_MIN_AGE && number <= YOUTH_MAX_AGE
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

  // 화면에는 입력한 값을 그대로 두되, 서버로는 범위 밖 나이를 빼고 보낸다.
  // number input 의 min/max 는 스피너만 제한하고 직접 타이핑은 막지 못해서,
  // 13 같은 값이 그대로 넘어가면 "나이 제한 없음" 정책이 전부 걸린다.
  // 백엔드가 422 로 거절하기도 하므로 여기서 먼저 정리한다.
  const query = useMemo(
    () => (isYouthAge(conditions.age) ? conditions : { ...conditions, age: '' }),
    [conditions],
  )

  return { conditions, query, update, reset }
}
