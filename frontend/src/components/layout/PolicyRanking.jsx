import { useEffect, useRef, useState } from 'react'
import { getPolicies } from '../../api/endpoints'

const TOP = 10
const ROTATE_MS = 2800

const prefersReducedMotion = () =>
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

// 조회수 상위 정책을 한 건씩 돌려 가며 보여준다. 오른쪽 버튼을 누르면 열 건이
// 한 번에 펼쳐진다.
//
// inqCnt 는 온통청년에서 수집한 시점의 누적 조회수다. 우리 서비스 조회수도
// 아니고 실시간도 아니라서 "실시간"이라는 말을 쓰지 않는다.
export default function PolicyRanking({ onPick }) {
  const [items, setItems] = useState([])
  const [index, setIndex] = useState(0)
  const [open, setOpen] = useState(false)
  const paused = useRef(false)

  useEffect(() => {
    let active = true
    getPolicies({}, { sort: 'popular', size: TOP })
      .then((data) => { if (active) setItems(data.items || []) })
      .catch(() => {})
    return () => { active = false }
  }, [])

  useEffect(() => {
    // 펼쳐 놓은 동안에는 돌리지 않는다. 읽는 중에 바뀌면 방해가 된다.
    if (items.length === 0 || open || prefersReducedMotion()) return undefined
    const timer = setInterval(() => {
      if (!paused.current) setIndex((current) => (current + 1) % items.length)
    }, ROTATE_MS)
    return () => clearInterval(timer)
  }, [items.length, open])

  if (items.length === 0) return null
  const current = items[index]

  return (
    <div
      className={`ranking${open ? ' is-open' : ''}`}
      onMouseEnter={() => { paused.current = true }}
      onMouseLeave={() => { paused.current = false }}
      onFocusCapture={() => { paused.current = true }}
      onBlurCapture={() => { paused.current = false }}
    >
      <div className="ranking-bar">
        <p className="ranking-label">청년들이 많이 찾은 정책</p>

        {/* 자동으로 바뀌는 자리라 스크린리더에는 읽어 주지 않는다.
            전체 목록이 접근 가능한 대안이다. */}
        <div className="ranking-stage" aria-hidden="true">
          <button type="button" key={current.plcy_no} onClick={() => onPick(current.title)}>
            <span className="ranking-number">{index + 1}</span>
            <span className="ranking-title">{current.title}</span>
            <span className="ranking-count">{current.view_count.toLocaleString()}회</span>
          </button>
        </div>

        <button
          type="button"
          className="ranking-toggle"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? '접기' : `${TOP}위까지 보기`}
          <span aria-hidden="true">⌄</span>
        </button>
      </div>

      {open && <ol className="ranking-list">
        {items.map((policy, rank) => (
          <li key={policy.plcy_no} style={{ '--ranking-delay': `${90 + rank * 32}ms` }}>
            <button type="button" onClick={() => onPick(policy.title)}>
              <span className="ranking-number">{rank + 1}</span>
              <span className="ranking-title">{policy.title}</span>
              <span className="ranking-count">{policy.view_count.toLocaleString()}회</span>
            </button>
          </li>
        ))}
      </ol>}
    </div>
  )
}
