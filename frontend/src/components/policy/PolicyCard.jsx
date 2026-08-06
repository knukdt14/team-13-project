const CATEGORY_TONE = [[/^일자리/, 'job'], [/^주거/, 'home'], [/^교육/, 'edu'], [/^(복지|금융)/, 'life'], [/^참여/, 'part']]
const toneOf = (category = '') => CATEGORY_TONE.find(([pattern]) => pattern.test(category))?.[1] || 'etc'

export default function PolicyCard({ policy }) {
  // '일자리,교육'처럼 대분류가 여럿인 정책이 105건 있다. 전에는 첫 번째만
  // 보여줘서, 교육 탭에서 찾은 정책이 카드에는 일자리로만 보였다.
  // 같은 값이 두 번 적힌 데이터('참여권리,참여권리')도 있어 중복을 지운다.
  const categories = [...new Set(policy.categories || [])].filter(Boolean)
  const category = categories[0] || '기타'
  const closed = policy.status === '마감'
  const urgent = policy.days_left != null && policy.days_left <= 30 && !closed
  return <li className={`policy-card tone-${toneOf(category)}${closed ? ' is-closed' : ''}`}>
    <div className="policy-card-top">
      <span className="policy-categories">
        {(categories.length ? categories : ['기타']).map((value) => (
          <span key={value} className={`policy-category tone-${toneOf(value)}`}>{value}</span>
        ))}
      </span>
      {closed ? <span className="closed-mark">마감</span> : urgent ? <span className="deadline">D-{policy.days_left}</span> : null}
    </div>
    <h3 className="policy-title">{policy.apply_url ? <a href={policy.apply_url} target="_blank" rel="noreferrer">{policy.title}</a> : policy.title}</h3>
    <p className="policy-org">{policy.organization}</p>
    {policy.summary && <p className="policy-summary">{policy.summary}</p>}
    <ul className="tags"><Tag text={policy.age_label} />{policy.regions?.map((value) => <Tag key={value} text={value} />)}{policy.jobs?.map((value) => <Tag key={value} text={value} open={value === '제한없음'} />)}</ul>
    {/* 기관이 공고에 적어 둔 문구 그대로다. 요약하거나 만들어내지 않는다.
        서류를 잘못 안내하면 사용자가 헛걸음한다.
        원문은 줄바꿈이 눌려 한 문단으로 오므로 백엔드가 항목별로 잘라 준다. */}
    {policy.documents?.length > 0 && <details className="policy-docs">
      <summary>준비 서류{policy.documents.length > 1 ? ` ${policy.documents.length}가지` : ''}</summary>
      <div className="policy-docs-body">
        {policy.documents.length > 1
          ? <ul>{policy.documents.map((item, index) => <li key={index}>{item}</li>)}</ul>
          : <p>{policy.documents[0]}</p>}
      </div>
      <p className="policy-docs-note">공고에 적힌 내용이에요. 신청 전에 기관 공고문을 꼭 확인해주세요.</p>
    </details>}
    <p className="policy-period">{policy.period_label}</p>
  </li>
}
function Tag({ text, open }) { return <li className={`tag${open ? ' is-open-cond' : ''}`}>{text}</li> }
