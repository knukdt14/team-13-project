import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { getMeta } from './api/endpoints'
import ConditionPanel from './components/conditions/ConditionPanel'
import Masthead from './components/layout/Masthead'
import TabNav from './components/layout/TabNav'
import useConditions from './hooks/useConditions'
import ChatPage from './pages/ChatPage'
import DirectApplyPage from './pages/DirectApplyPage'
import HomePage from './pages/HomePage'
import ListPage from './pages/ListPage'
import MapPage from './pages/MapPage'

export default function App() {
  const [meta, setMeta] = useState(null)
  const [error, setError] = useState(null)
  const { pathname } = useLocation()
  const isHome = pathname === '/'
  // conditions 는 화면에 보여줄 입력값, query 는 서버로 보낼 값이다.
  // 청년 범위(15~49세) 밖 나이는 query 에서 빠진다.
  const { conditions, query, update, reset } = useConditions()
  useEffect(() => { getMeta().then(setMeta).catch((caught) => setError(caught.message)) }, [])
  useEffect(() => { window.scrollTo({ top: 0, left: 0, behavior: 'auto' }) }, [pathname])
  return <div className="app">
    {isHome
      ? <Masthead total={meta?.total} isHome />
      : <div className="app-topbar"><TabNav /></div>}
    <main className={`body${isHome ? ' is-home' : ''}`}>{error && <p className="alert">{error}</p>}{isHome
      ? <Routes><Route path="/" element={<HomePage />} /></Routes>
      : <div className="columns">
        <ConditionPanel meta={meta} conditions={conditions} onChange={update} onReset={reset} />
        <section className="stage"><Routes>
          <Route path="/chat" element={<ChatPage conditions={query} total={meta?.total} />} />
          <Route path="/apply" element={<DirectApplyPage conditions={query} />} />
          <Route path="/map" element={<MapPage conditions={query} onPickRegion={(region) => update({ region })} />} />
          <Route path="/documents" element={<ListPage conditions={query} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes></section>
      </div>}
    </main>
    <footer className="colophon"><strong>청년정책도우미</strong><span>경북대학교 KDT 14기 웹 프로젝트 3팀</span><span>실제 신청 전에는 각 기관 공고문을 꼭 확인해주세요</span></footer>
  </div>
}
