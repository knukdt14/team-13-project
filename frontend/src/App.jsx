import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { getMeta } from './api/endpoints'
import ConditionPanel from './components/conditions/ConditionPanel'
import Masthead from './components/layout/Masthead'
import TabNav from './components/layout/TabNav'
import useConditions from './hooks/useConditions'
import ChatPage from './pages/ChatPage'
import ListPage from './pages/ListPage'
import MapPage from './pages/MapPage'

export default function App() {
  const [meta, setMeta] = useState(null)
  const [error, setError] = useState(null)
  const { conditions, update, reset } = useConditions()
  useEffect(() => { getMeta().then(setMeta).catch((caught) => setError(caught.message)) }, [])
  return <div className="app">
    <Masthead total={meta?.total} /><TabNav />
    <main className="body">{error && <p className="alert">{error}</p>}<div className="columns">
      <ConditionPanel meta={meta} conditions={conditions} onChange={update} onReset={reset} />
      <section className="stage"><Routes>
        <Route path="/" element={<ChatPage conditions={conditions} total={meta?.total} />} />
        <Route path="/map" element={<MapPage conditions={conditions} onPickRegion={(region) => update({ region })} />} />
        <Route path="/documents" element={<ListPage conditions={conditions} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes></section>
    </div></main>
    <footer className="colophon"><strong>청년정책도우미</strong><span>경북대학교 KDT 14기 웹 프로젝트 3팀</span><span>실제 신청 전에는 각 기관 공고문을 꼭 확인해주세요</span></footer>
  </div>
}
