import { useEffect, useState } from 'react'
import { getPolicies } from '../api/endpoints'
import PolicyCardList from '../components/policy/PolicyCardList'
import useDebounced from '../hooks/useDebounced'

export default function ListPage({ conditions }) {
  const [keyword, setKeyword] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const query = useDebounced(keyword)
  useEffect(() => {
    setLoading(true); setError(null)
    getPolicies(conditions, { q: query, size: 48 }).then(setData).catch((caught) => setError(caught.message)).finally(() => setLoading(false))
  }, [conditions, query])
  return <div className="list"><div className="list-head"><input className="input" type="search" value={keyword} placeholder="월세, 창업, 자격증…" onChange={(event) => setKeyword(event.target.value)} />{data && <p className="list-count"><strong>{data.matched.toLocaleString()}</strong>건 찾았어요{loading && <span className="muted"> · 갱신 중</span>}</p>}</div>{error && <p className="alert">{error}</p>}<PolicyCardList policies={data?.items || []} />{data?.items.length === 0 && <p className="muted">조건에 맞는 정책이 없어요. 마감 정책이나 전국 정책 보기를 켜보세요.</p>}</div>
}
