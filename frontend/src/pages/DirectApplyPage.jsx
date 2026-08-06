import { useEffect, useRef, useState } from 'react'
import { getPolicies } from '../api/endpoints'

const PAGE_SIZE = 12
const TONES = [[/^일자리/, 'job'], [/^주거/, 'home'], [/^교육/, 'edu'], [/^(복지|금융)/, 'life'], [/^참여/, 'part']]
const toneOf = (category = '') => TONES.find(([pattern]) => pattern.test(category))?.[1] || 'etc'

function hostname(url) {
  try { return new URL(url).hostname.replace(/^www\./, '') }
  catch { return '외부 기관 사이트' }
}

function ApplyCard({ policy }) {
  const category = policy.categories?.[0] || '기타'
  const deadline = policy.days_left == null ? '상시·기간 확인' : policy.days_left === 0 ? '오늘 마감' : `D-${policy.days_left}`
  return <article className={`apply-card tone-${toneOf(category)}`}>
    <div className="apply-card-top"><span className="policy-category">{category}</span><span className="apply-deadline">{deadline}</span></div>
    <div className="apply-card-copy"><h3>{policy.title}</h3><p className="apply-organization">{policy.organization}</p></div>
    <div className="apply-card-conditions"><span>{policy.age_label}</span>{policy.regions?.slice(0, 2).map((region) => <span key={region}>{region}</span>)}<span>{policy.period_label}</span></div>
    <div className="apply-card-links">
      {policy.reference_url && policy.reference_url !== policy.application_url && <a className="apply-reference" href={policy.reference_url} target="_blank" rel="noreferrer">공고 먼저 보기</a>}
      <a className="apply-primary" href={policy.application_url} target="_blank" rel="noreferrer"><span><small>{hostname(policy.application_url)}에서</small>신청 페이지 열기</span><b aria-hidden="true">↗</b></a>
    </div>
  </article>
}

export default function DirectApplyPage({ conditions }) {
  const pageTopRef = useRef(null)
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const queryKey = JSON.stringify(conditions)
  const previousQuery = useRef(queryKey)

  useEffect(() => {
    if (previousQuery.current !== queryKey) {
      previousQuery.current = queryKey
      if (page !== 1) { setPage(1); return undefined }
    }
    let active = true
    setLoading(true)
    setError(null)
    getPolicies(conditions, { direct_apply_only: true, sort: 'deadline', page, size: PAGE_SIZE })
      .then((response) => { if (active) setData(response) })
      .catch((caught) => { if (active) setError(caught.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [conditions, page, queryKey])

  const pages = Math.max(1, Math.ceil((data?.matched || 0) / PAGE_SIZE))
  const changePage = (nextPage) => {
    if (nextPage < 1 || nextPage > pages || nextPage === page) return
    setPage(nextPage)
    pageTopRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return <div className="apply-page" ref={pageTopRef}>
    <header className="apply-hero">
      <div><p className="section-kicker">기관 신청 페이지로 바로 연결해요</p><h2>찾았다면 바로 신청해보세요</h2><p>신청 주소가 확인된 정책만 모았어요. 신청은 외부 기관 사이트에서 진행돼요.</p></div>
      <div className="apply-hero-count"><span>바로 이동 가능한 정책</span><strong>{data?.matched?.toLocaleString() || '—'}<small>건</small></strong></div>
    </header>
    {error && <p className="alert">{error}</p>}
    {loading && <div className="apply-loading" role="status">신청 가능한 정책을 모으고 있어요<span className="dots" aria-hidden="true"><i /><i /><i /></span></div>}
    {!loading && <div className="apply-grid">{(data?.items || []).map((policy) => <ApplyCard key={policy.plcy_no} policy={policy} />)}</div>}
    {!loading && !error && data?.items.length === 0 && <div className="home-empty"><strong>현재 조건에서 바로 신청할 정책을 찾지 못했어요</strong><p>왼쪽 조건을 조금 넓히거나 전국 정책 보기를 켜보세요.</p></div>}
    {data?.matched > PAGE_SIZE && <nav className="apply-pagination" aria-label="바로 신청 정책 페이지"><button type="button" className="button-ghost" disabled={page === 1 || loading} onClick={() => changePage(page - 1)}>이전</button><span>{page} / {pages}</span><button type="button" className="button-ghost" disabled={page >= pages || loading} onClick={() => changePage(page + 1)}>다음</button></nav>}
  </div>
}
