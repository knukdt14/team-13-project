import { useEffect, useState } from 'react'
import { getPolicies, getRegionSummary } from '../api/endpoints'
import KakaoMap from '../components/map/KakaoMap'

export default function MapPage({ conditions, onPickRegion }) {
  const [summary, setSummary] = useState(null)
  const [region, setRegion] = useState(null)
  const [policies, setPolicies] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => { setError(null); getRegionSummary(conditions).then(setSummary).catch((caught) => setError(caught.message)) }, [conditions])
  const select = (item) => {
    const count = summary?.regions.find((value) => value.code === item.code)?.count || item.count || 0
    setRegion({ ...item, count }); setPolicies(null)
    getPolicies({ ...conditions, region: item.code }, { size: 30 }).then((response) => setPolicies(response.items)).catch((caught) => { setError(caught.message); setPolicies([]) })
  }
  return <>{error && <p className="alert">{error}</p>}<KakaoMap summary={summary} region={region} policies={policies} onSelect={select} onClose={() => { setRegion(null); setPolicies(null) }} onApply={() => { onPickRegion(region.code); setRegion(null); setPolicies(null) }} /></>
}
