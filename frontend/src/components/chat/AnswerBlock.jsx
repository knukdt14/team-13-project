import PolicyCardList from '../policy/PolicyCardList'

export default function AnswerBlock({ message }) {
  const policies = (message.sources || []).map((source) => source.policy).filter(Boolean)
  return <div className="answer">
    {message.used_attachments && <p className="answer-tag">첨부한 문서를 읽고 답했어요</p>}
    <p className="answer-text">{message.text}</p>
    {message.elapsed_ms != null && <div className="answer-meta">조건에 맞는 정책 {message.matched?.toLocaleString() || 0}건 · 전체 {message.total?.toLocaleString() || 0}건 · {(message.elapsed_ms / 1000).toFixed(1)}초</div>}
    {policies.length > 0 && <div className="sources"><p className="sources-title">{message.relevant === false ? '딱 맞는 정책은 없지만, 조건에 맞는 다른 정책이에요' : '이 정책들을 보고 답했어요'}</p><PolicyCardList policies={policies} /></div>}
  </div>
}
