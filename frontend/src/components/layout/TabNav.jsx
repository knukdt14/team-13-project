import { useLayoutEffect, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

const TABS = [
  { to: '/', label: '정책 상담', end: true },
  { to: '/map', label: '지역별 탐색' },
  { to: '/documents', label: '정책 목록' },
]

// .tabs-inner 는 로고·히어로와 같은 정렬 컨테이너다(폭 제한 + 가운데 정렬).
// 여기에 알약 배경까지 얹으면 배경이 컨테이너 전체로 늘어나므로,
// .tabs-pill 을 한 겹 두고 그 위에 배경을 그린다.
//
// 검은 알약은 탭마다 따로 그리지 않는다. 하나짜리 .tab-indicator 를 두고
// 활성 탭의 위치·너비로 옮긴다. 그래야 탭을 누를 때 사라졌다 나타나지 않고
// 미끄러져 이동한다.
export default function TabNav() {
  const pillRef = useRef(null)
  const [box, setBox] = useState(null)
  const { pathname } = useLocation()

  // useLayoutEffect 는 그리기 전에 실행된다. 첫 화면부터 알약이 제자리에
  // 있으므로 왼쪽 끝에서 미끄러져 들어오는 일이 없다.
  useLayoutEffect(() => {
    const pill = pillRef.current
    if (!pill) return undefined
    const measure = () => {
      const active = pill.querySelector('.tab.is-active')
      if (active) setBox({ left: active.offsetLeft, width: active.offsetWidth })
    }
    measure()
    // 창 크기나 폰트 로딩으로 탭 너비가 바뀌면 다시 잰다.
    const observer = new ResizeObserver(measure)
    observer.observe(pill)
    return () => observer.disconnect()
  }, [pathname])

  return <nav className="tabs" aria-label="화면 선택"><div className="tabs-inner">
    <div className="tabs-pill" ref={pillRef}>
      <span
        className="tab-indicator"
        aria-hidden="true"
        style={box
          ? { transform: `translateX(${box.left}px)`, width: `${box.width}px` }
          : { opacity: 0 }}
      />
      {TABS.map((tab) => <NavLink key={tab.to} to={tab.to} end={tab.end} className={({ isActive }) => `tab${isActive ? ' is-active' : ''}`}>{tab.label}</NavLink>)}
    </div>
  </div></nav>
}
