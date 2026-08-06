import { useEffect, useRef, useState } from 'react'

const prefersReducedMotion = () =>
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

// 숫자가 0에서 목표값까지 올라간다. 히어로의 "모아본 청년정책 2,698건"에 쓴다.
// 값이 API 로 늦게 오므로, 도착한 시점부터 센다. 그래서 로딩이 끝났다는
// 신호도 겸한다.
export default function useCountUp(target, { duration = 900, delay = 0 } = {}) {
  const [value, setValue] = useState(null)
  const frameRef = useRef(0)

  useEffect(() => {
    if (target == null) return undefined
    if (prefersReducedMotion()) {
      setValue(target)
      return undefined
    }
    let startedAt
    const timer = setTimeout(() => {
      const step = (now) => {
        startedAt ??= now
        const progress = Math.min((now - startedAt) / duration, 1)
        // ease-out cubic — 빠르게 올라가다 끝에서 부드럽게 멈춘다
        setValue(Math.round(target * (1 - (1 - progress) ** 3)))
        if (progress < 1) frameRef.current = requestAnimationFrame(step)
      }
      frameRef.current = requestAnimationFrame(step)
    }, delay)

    return () => {
      clearTimeout(timer)
      cancelAnimationFrame(frameRef.current)
    }
  }, [target, duration, delay])

  return value
}
