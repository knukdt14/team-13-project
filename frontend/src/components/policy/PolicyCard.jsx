const CATEGORY_TONE = [[/^일자리/, 'job'], [/^주거/, 'home'], [/^교육/, 'edu'], [/^(복지|금융)/, 'life'], [/^참여/, 'part']]
const toneOf = (category = '') => CATEGORY_TONE.find(([pattern]) => pattern.test(category))?.[1] || 'etc'

export default function PolicyCard({ policy }) {
  const category = policy.categories?.[0] || '기타'
  const closed = policy.status === '마감'
  const urgent = policy.days_left != null && policy.days_left <= 30 && !closed
  return <li className={`policy-card tone-${toneOf(category)}${closed ? ' is-closed' : ''}`}>
    <div className="policy-card-top"><span className="policy-category">{category}</span>{closed ? <span className="closed-mark">마감</span> : urgent ? <span className="deadline">D-{policy.days_left}</span> : null}</div>
    <h3 className="policy-title">{policy.apply_url ? <a href={policy.apply_url} target="_blank" rel="noreferrer">{policy.title}</a> : policy.title}</h3>
    <p className="policy-org">{policy.organization}</p>
    {policy.summary && <p className="policy-summary">{policy.summary}</p>}
    <ul className="tags"><Tag text={policy.age_label} />{policy.regions?.map((value) => <Tag key={value} text={value} />)}{policy.jobs?.map((value) => <Tag key={value} text={value} open={value === '제한없음'} />)}</ul>
    <p className="policy-period">{policy.period_label}</p>
  </li>
}
function Tag({ text, open }) { return <li className={`tag${open ? ' is-open-cond' : ''}`}>{text}</li> }
