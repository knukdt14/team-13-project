import { NavLink } from 'react-router-dom'

const TABS = [
  { to: '/', label: '정책 상담', end: true },
  { to: '/map', label: '지역별 탐색' },
  { to: '/documents', label: '정책 목록' },
]

export default function TabNav() {
  return <nav className="tabs" aria-label="화면 선택"><div className="tabs-inner">
    {TABS.map((tab) => <NavLink key={tab.to} to={tab.to} end={tab.end} className={({ isActive }) => `tab${isActive ? ' is-active' : ''}`}>{tab.label}</NavLink>)}
  </div></nav>
}
