import useKakaoMap from '../../hooks/useKakaoMap'
import HoverLabel from './HoverLabel'
import MapLegend from './MapLegend'
import RegionPanel from './RegionPanel'

export default function KakaoMap({ summary, region, policies, onSelect, onClose, onApply }) {
  const map = useKakaoMap({ summary, selectedCode: region?.code, onSelect })
  if (!map.hasKey) return <div className="map-fallback"><div className="notice-box"><h3>카카오맵 키가 아직 없어요</h3><p><code>frontend/.env</code>에 <code>VITE_KAKAO_MAP_KEY</code>를 넣으면 지도가 나타나요. 아래 지역 목록은 바로 사용할 수 있어요.</p></div>{summary && <div className="box"><h3 className="box-title">시도별 정책 수</h3><ul className="bars">{summary.regions.map((item) => <li key={item.code}><button className="bar-row" onClick={() => onSelect(item)}><span>{item.name}</span><span className="bar-track"><span className="bar-fill" style={{ width: `${summary.max ? item.count / summary.max * 100 : 0}%` }} /></span><span className="bar-count">{item.count}</span></button></li>)}</ul></div>}</div>
  const close = () => { map.reset(); onClose() }
  return <div className="map-wrap"><header className="map-head">
    <div><p className="section-kicker">지도에서 한눈에</p><h2>사는 지역을 눌러 정책을 찾아봐요</h2><p>지역을 선택하면 그곳에서 신청할 수 있는 정책을 바로 보여드려요.</p></div>
    {summary && <div className="map-metrics"><span><small>지역 정책</small><strong>{(summary.matched - summary.nationwide).toLocaleString()}<em>건</em></strong></span><span><small>전국 정책 제외</small><strong>{summary.nationwide.toLocaleString()}<em>건</em></strong></span></div>}
  </header>{map.error && <p className="alert">{map.error}</p>}<div className="map-stage"><div ref={map.containerRef} className="map-canvas" />{!region && <div className="map-guide" aria-hidden="true"><span>1</span><p><strong>지역을 선택해보세요</strong><small>지도 위 시·도를 누르면 정책이 열려요</small></p></div>}<HoverLabel region={map.hovered} /><MapLegend summary={summary} /><RegionPanel region={region} policies={policies} onClose={close} onApply={onApply} /></div></div>
}
