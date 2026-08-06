import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getPolicies } from '../api/endpoints'

// 히어로에서 이미 "물어보기"를 받았으니, 여기서는 나머지 길을 보여준다.
// 숫자는 실제로 세어서 넣는다. 비어 있는 길로 보내면 안 된다.
const PATHS = [
  {
    to: '/apply',
    kicker: '찾는 데서 끝내지 않도록',
    title: '지금 바로 신청할 수 있는 정책',
    body: '신청 주소가 확인된 정책만 모아 마감이 가까운 순서로 보여드려요.',
    unit: '건',
    key: 'apply',
  },
  {
    to: '/documents',
    kicker: '조건으로 좁혀보기',
    title: '접수 중인 정책 전체',
    body: '나이·지역·취업상태를 넣으면 해당하는 정책만 남아요.',
    unit: '건',
    key: 'open',
  },
  {
    to: '/map',
    kicker: '우리 동네부터',
    title: '지도에서 지역별로 찾기',
    body: '시도를 누르면 그 지역 청년정책이 몇 건인지 바로 보여요.',
    unit: '개 시도',
    key: 'sido',
  },
]

export default function HomePage() {
  const [counts, setCounts] = useState({ apply: null, open: null, sido: 17 })

  useEffect(() => {
    let active = true
    Promise.all([
      getPolicies({}, { size: 1 }),
      getPolicies({}, { direct_apply_only: true, size: 1 }),
    ])
      .then(([open, apply]) => {
        if (active) setCounts((current) => ({ ...current, open: open.matched, apply: apply.matched }))
      })
      .catch(() => {})
    return () => { active = false }
  }, [])

  return <div className="home">
    <section className="home-paths" aria-label="정책을 찾는 다른 방법">
      {PATHS.map((path) => (
        <Link key={path.to} className="home-path" to={path.to}>
          <p className="section-kicker">{path.kicker}</p>
          <h2>{path.title}</h2>
          <p className="home-path-body">{path.body}</p>
          <p className="home-path-count">
            <strong>{counts[path.key]?.toLocaleString() ?? '—'}</strong>
            <small>{path.unit}</small>
            <span className="home-path-go" aria-hidden="true">→</span>
          </p>
        </Link>
      ))}
    </section>

    <section className="home-document-cta">
      <div className="document-visual" aria-hidden="true"><span>PDF</span><span>가</span><i>✓</i></div>
      <div>
        <p className="section-kicker">공고문이 어렵다면</p>
        <h2>공고문을 올리면 쉬운 말로 풀어드려요</h2>
        {/* 자격 판정이나 준비 서류는 약속하지 않는다. 서류 데이터가 없고,
            조건 자동 판정은 아직 신뢰할 만큼 정확하지 않다. */}
        <p>PDF나 포스터 사진을 올리고 궁금한 걸 이어서 물어보세요. 신청 자격은 기관 공고문에서 꼭 다시 확인해주세요.</p>
      </div>
      <Link className="button" to="/chat">공고문 올리고 물어보기</Link>
    </section>
  </div>
}
