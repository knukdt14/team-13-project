export default function MapLegend({ summary }) {
  if (!summary) return null
  return <div className="map-legend">
    <p className="legend-title">지역별 정책 수</p>
    <div className="legend-scale"><span className="legend-bar" /><span className="legend-min">1</span><span className="legend-max">{summary.max.toLocaleString()}</span></div>
    <p className="legend-empty"><span className="legend-swatch" />지금 신청할 수 있는 정책 없음</p>
  </div>
}
