import useKakaoMap from '../../hooks/useKakaoMap'
import HoverLabel from './HoverLabel'
import MapLegend from './MapLegend'
import RegionPanel from './RegionPanel'

export default function KakaoMap({ summary, region, policies, onSelect, onClose, onApply }) {
  const map = useKakaoMap({ summary, selectedCode: region?.code, onSelect })
  if (!map.hasKey) return <div className="map-fallback"><div className="notice-box"><h3>카카오맵 키가 아직 없어요</h3><p><code>frontend/.env</code>에 <code>VITE_KAKAO_MAP_KEY</code>를 넣으면 지도가 나타나요. 아래 지역 목록은 바로 사용할 수 있어요.</p></div>{summary && <div className="box"><h3 className="box-title">시도별 정책 수</h3><ul className="bars">{summary.regions.map((item) => <li key={item.code}><button className="bar-row" onClick={() => onSelect(item)}><span>{item.name}</span><span className="bar-track"><span className="bar-fill" style={{ width: `${summary.max ? item.count / summary.max * 100 : 0}%` }} /></span><span className="bar-count">{item.count}</span></button></li>)}</ul></div>}</div>
  const close = () => { map.reset(); onClose() }
  return <div className="map-wrap"><div className="map-head"><p>지역을 누르면 그곳 정책을 보여드려요. {summary && <>지금 지도에는 <strong>{(summary.matched - summary.nationwide).toLocaleString()}</strong>건이 담겨 있어요. 전국 정책 {summary.nationwide.toLocaleString()}건은 뺐어요.</>}</p></div>{map.error && <p className="alert">{map.error}</p>}<div className="map-stage"><div ref={map.containerRef} className="map-canvas" /><HoverLabel region={map.hovered} /><MapLegend summary={summary} /><RegionPanel region={region} policies={policies} onClose={close} onApply={onApply} /></div></div>
}
