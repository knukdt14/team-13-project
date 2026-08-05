import { NavLink } from 'react-router-dom'

const TABS = [
  { to: '/', label: '정책 상담', end: true },
  { to: '/map', label: '지역별 탐색' },
  { to: '/documents', label: '정책 목록' },
]

// .tabs-inner 는 로고·히어로와 같은 정렬 컨테이너다(폭 제한 + 가운데 정렬).
// 여기에 알약 배경까지 얹으면 배경이 컨테이너 전체로 늘어나므로,
// .tabs-pill 을 한 겹 두고 그 위에 배경을 그린다.
export default function TabNav() {
  return <nav className="tabs" aria-label="화면 선택"><div className="tabs-inner">
    <div className="tabs-pill">
      {TABS.map((tab) => <NavLink key={tab.to} to={tab.to} end={tab.end} className={({ isActive }) => `tab${isActive ? ' is-active' : ''}`}>{tab.label}</NavLink>)}
    </div>
  </div></nav>
}
