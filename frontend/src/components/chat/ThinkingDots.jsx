export default function ThinkingDots({ label = '정책을 찾아보고 있어요' }) {
  return <div className="thinking"><span className="dots" aria-hidden="true"><i /><i /><i /></span>{label}<em> · 답이 오는 대로 바로 보여드려요</em></div>
}
