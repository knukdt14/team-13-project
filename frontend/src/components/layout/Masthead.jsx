import useCountUp from '../../hooks/useCountUp'

// 히어로 미리보기는 이 서비스가 하는 일을 2.5초 동안 재연한다.
// 질문이 올라가고 → 점 세 개가 뜨고 → 답이 도착하고 → 분야 태그가 붙고
// → 건수가 올라간다. 정지된 스크린샷 대신 제품 자체를 보여주는 셈이다.
// 순서는 components.css 의 animation-delay 가 맡는다.
export default function Masthead({ total }) {
  const counted = useCountUp(total, { delay: 2350 })

  return (
    <header className="masthead">
      <div className="masthead-inner">
        <p className="brand">
          <span className="brand-mark" aria-hidden="true"><span /></span>
          <span>청년정책<span className="brand-accent">도우미</span></span>
        </p>
        <p className="brand-note"><span aria-hidden="true">●</span> 청년정책 {total?.toLocaleString() || '—'}건을 살펴볼 수 있어요</p>
      </div>
      <div className="hero">
        <div className="hero-copy">
          <p className="hero-kicker"><span aria-hidden="true">✦</span> 어려운 공고문은 이제 그만</p>
          <h1>
            <span className="hero-line">놓치기 아까운 혜택,</span>
            <span className="hero-line"><em>내게 맞는 것만</em> 찾아봐요</span>
          </h1>
          <p className="hero-description">나이와 지역을 알려주면 복잡한 청년정책을<br className="desktop-break" /> 쉽고 빠르게 골라드려요.</p>
        </div>
        <div className="hero-preview" aria-hidden="true">
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
      </div>
    </header>
  )
}
