import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import useCountUp from '../../hooks/useCountUp'
import PolicyRanking from './PolicyRanking'

const RECOMMENDED_QUESTIONS = [
  '대구에서 받을 수 있는 월세 지원이 있어?',
  '취업 준비 중인데 받을 수 있는 지원금은?',
  '자격증 시험비를 지원하는 정책을 찾아줘',
  '신청 마감이 가까운 정책부터 보여줘',
]

function tiltPreview(event) {
  if (event.pointerType === 'touch') return
  const card = event.currentTarget
  const bounds = card.getBoundingClientRect()
  const horizontal = (event.clientX - bounds.left) / bounds.width - 0.5
  const vertical = (event.clientY - bounds.top) / bounds.height - 0.5
  card.style.setProperty('--preview-tilt-x', `${vertical * -8}deg`)
  card.style.setProperty('--preview-tilt-y', `${horizontal * 10}deg`)
}

function resetPreview(event) {
  event.currentTarget.style.setProperty('--preview-tilt-x', '0deg')
  event.currentTarget.style.setProperty('--preview-tilt-y', '0deg')
}

// 히어로 미리보기는 이 서비스가 하는 일을 2.5초 동안 재연한다.
// 질문이 올라가고 → 점 세 개가 뜨고 → 답이 도착하고 → 분야 태그가 붙고
// → 건수가 올라간다. 정지된 스크린샷 대신 제품 자체를 보여주는 셈이다.
// 순서는 components.css 의 animation-delay 가 맡는다.
export default function Masthead({ total, isHome = false }) {
  const counted = useCountUp(total, { delay: 2350 })
  const navigate = useNavigate()
  const [question, setQuestion] = useState('')

  // 히어로에서 바로 물어볼 수 있게 한다. 예전에는 "30초 맞춤 정책 찾기" 같은
  // 버튼이 /chat 으로 보냈는데, 그게 챗봇이라는 걸 알 방법이 없었다.
  // 입력창이 있으면 설명이 필요 없다.
  const ask = (text) => {
    const trimmed = text.trim()
    navigate(trimmed ? `/chat?q=${encodeURIComponent(trimmed)}` : '/chat')
  }

  return (
    <header className={`masthead${isHome ? '' : ' is-compact'}`}>
      <div className="masthead-inner">
        <p className="brand">
          <span className="brand-mark" aria-hidden="true"><span /></span>
          <span>청년정책<span className="brand-accent">도우미</span></span>
        </p>
        <p className="brand-note"><span aria-hidden="true">●</span> 청년정책 {total?.toLocaleString() || '—'}건을 살펴볼 수 있어요</p>
      </div>
      {isHome && <div className="hero">
        <div className="hero-copy">
          <p className="hero-kicker"><span aria-hidden="true">✦</span> 어려운 공고문은 이제 그만</p>
          <h1>
            <span className="hero-line">놓치기 아까운 혜택,</span>
            <span className="hero-line"><em>내게 맞는 것만</em> 찾아봐요</span>
          </h1>
          <p className="hero-description">나이와 지역을 알려주면 복잡한 청년정책을<br className="desktop-break" /> 쉽고 빠르게 골라드려요.</p>

          <form className="hero-ask" onSubmit={(event) => { event.preventDefault(); ask(question) }}>
            <input
              className="hero-ask-input"
              type="text"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="어떤 지원이 궁금하세요?"
              aria-label="정책 상담 질문"
            />
            <button className="hero-ask-send" type="submit">
              정책 찾기
            </button>
          </form>

          <div className="hero-suggestions">
            <p>이렇게 물어보세요</p>
            <ul>{RECOMMENDED_QUESTIONS.map((item) => <li key={item}><button type="button" onClick={() => ask(item)}>{item}</button></li>)}</ul>
          </div>
        </div>
        <div className="hero-showcase">
          <div className="hero-preview" aria-hidden="true" onPointerMove={tiltPreview} onPointerLeave={resetPreview}>
            <div className="preview-question">나도 받을 수 있는 지원이 있을까?</div>
            <div className="preview-reply">
              <div className="preview-thinking"><span className="dots"><i /><i /><i /></span></div>
              <div className="preview-answer">
                <span className="preview-spark">✦</span>
                <div><strong>딱 맞는 정책부터 찾아볼게요</strong><p>조건을 넣을수록 더 정확해져요</p><div className="preview-tags"><span>일자리</span><span>주거</span><span>교육</span></div></div>
              </div>
            </div>
            <div className="preview-stat"><span>모아본 청년정책</span><strong>{(counted ?? 0).toLocaleString()}<small>건</small></strong></div>
          </div>
          <div className="hero-ranking"><PolicyRanking onPick={(title) => navigate(`/documents?q=${encodeURIComponent(title)}`)} /></div>
        </div>
      </div>}
    </header>
  )
}
