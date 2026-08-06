import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getPolicies } from '../api/endpoints'
import PolicyCardList from '../components/policy/PolicyCardList'
import useDebounced from '../hooks/useDebounced'

const PAGE_SIZE = 12
const CATEGORIES = [
  { label: '전체', value: '', tone: 'all' },
  { label: '일자리', value: '일자리', tone: 'job' },
  { label: '주거', value: '주거', tone: 'home' },
  { label: '교육', value: '교육', tone: 'edu' },
  { label: '복지·문화', value: '복지', tone: 'life' },
  { label: '참여·권리', value: '참여', tone: 'part' },
]

export default function ListPage({ conditions }) {
  const listRef = useRef(null)
  const [searchParams] = useSearchParams()
  const initialQuery = searchParams.get('q') || ''
  const initialCategory = CATEGORIES.some((category) => category.value === initialQuery) ? initialQuery : ''
  const [keyword, setKeyword] = useState(() => initialCategory ? '' : initialQuery)
  const [category, setCategory] = useState(initialCategory)
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const query = useDebounced(keyword)

  // 카테고리를 q 로 보내면 안 된다. q 는 제목·키워드까지 훑어서, 키워드가
  // '교육지원'인 일자리 정책이 교육 탭에 섞여 나온다. category 는 대분류만 본다.
  useEffect(() => { setPage(1) }, [conditions, query, category])

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    getPolicies(conditions, { q: query, category, page, size: PAGE_SIZE })
      .then((response) => { if (active) setData(response) })
      .catch((caught) => { if (active) setError(caught.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [conditions, query, category, page])

  const pageCount = Math.max(1, Math.ceil((data?.matched || 0) / PAGE_SIZE))
  const pageNumbers = useMemo(() => {
    const length = Math.min(5, pageCount)
    const start = Math.max(1, Math.min(page - 2, pageCount - length + 1))
    return Array.from({ length }, (_, index) => start + index)
  }, [page, pageCount])

  const changePage = (nextPage) => {
    if (nextPage === page || nextPage < 1 || nextPage > pageCount) return
    setPage(nextPage)
    listRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const chooseCategory = (value) => {
    setCategory(value && category === value ? '' : value)
    setKeyword('')
  }

  const changeKeyword = (value) => {
    setKeyword(value)
    if (category) setCategory('')
  }

  return <div className="list" ref={listRef}>
    <div className="list-head">
      <input className="input" type="search" value={keyword} placeholder="월세, 창업, 자격증…" onChange={(event) => changeKeyword(event.target.value)} />
      {data && <p className="list-count"><strong>{data.matched.toLocaleString()}</strong>건 · {page}/{pageCount}페이지{loading && <span className="muted"> · 갱신 중</span>}</p>}
    </div>
    <div className="list-categories" role="group" aria-label="정책 분야 선택">
      {CATEGORIES.map((item) => <button key={item.label} type="button" className={`category-filter tone-${item.tone}${category === item.value ? ' is-active' : ''}`} aria-pressed={category === item.value} onClick={() => chooseCategory(item.value)}><span aria-hidden="true" />{item.label}</button>)}
    </div>
    {error && <p className="alert">{error}</p>}
    <PolicyCardList policies={data?.items || []} />
    {data?.items.length === 0 && <p className="muted">조건에 맞는 정책이 없어요. 마감 정책이나 전국 정책 보기를 켜보세요.</p>}
    {!error && pageCount > 1 && <nav className="list-pagination" aria-label="정책 목록 페이지">
      <button type="button" onClick={() => changePage(page - 1)} disabled={page === 1} aria-label="이전 페이지">←</button>
      {pageNumbers.map((number) => <button key={number} type="button" className={number === page ? 'is-current' : ''} aria-current={number === page ? 'page' : undefined} onClick={() => changePage(number)}>{number}</button>)}
      <button type="button" onClick={() => changePage(page + 1)} disabled={page === pageCount} aria-label="다음 페이지">→</button>
    </nav>}
  </div>
}
