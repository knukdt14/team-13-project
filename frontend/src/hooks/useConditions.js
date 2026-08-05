import { useCallback, useMemo, useState } from 'react'

const STORAGE_KEY = 'youth-policy-conditions'
export const EMPTY_CONDITIONS = {
  age: '', employment: '', education: '', region: '',
  include_closed: false, include_nationwide: false,
}

// ⚠️ src/shared/constants.py 의 YOUTH_MIN_AGE / YOUTH_MAX_AGE 와 같은 값이어야 한다.
// 자바스크립트가 파이썬을 읽을 수 없어 여기만 손으로 맞춘다.
// 범위를 바꿀 일이 있으면 파이썬 쪽을 먼저 고치고 이 두 줄을 따라 고친다.
// 근거(데이터 분포)도 그 파일에 적어 두었다.
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
