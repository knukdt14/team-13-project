import PolicyCardList from '../policy/PolicyCardList'

export default function RegionPanel({ region, policies, onClose, onApply }) {
  return <div className={`region-panel${region ? ' is-open' : ''}`} aria-hidden={!region}>{region && <>
    <div className="region-head"><div><h3>{region.name}</h3><p>정책 {region.count.toLocaleString()}건</p></div><button className="icon-button" onClick={onClose} aria-label="닫기">✕</button></div>
    <div className="region-body">{!policies && <p className="muted">불러오는 중…</p>}{policies?.length === 0 && <p className="muted">지금 신청할 수 있는 정책이 없어요. 마감 정책이나 전국 정책 보기를 켜보세요.</p>}<PolicyCardList policies={policies || []} /></div>
    <div className="region-foot"><button className="button" onClick={onApply}>이 지역으로 조건 설정</button></div>
  </>}</div>
}
