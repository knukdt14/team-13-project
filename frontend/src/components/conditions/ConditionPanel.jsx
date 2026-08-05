export default function ConditionPanel({ meta, conditions, onChange, onReset }) {
  const dirty = Object.values(conditions).some(Boolean)
  return <aside className="conditions"><div className="box">
    <div className="condition-heading"><span className="condition-icon" aria-hidden="true">✓</span><div><p className="condition-kicker">맞춤 찾기</p><h2 className="box-title">내 조건</h2></div></div>
    <p className="box-note" style={{ margin: '0 0 8px' }}>입력할수록 나에게 맞는 정책만 남아요</p>
    <Row label="나이"><AgeField value={conditions.age} onChange={(age) => onChange({ age })} /></Row>
    <Row label="취업상태"><Select label="취업상태" value={conditions.employment} onChange={(employment) => onChange({ employment })} options={meta?.jobs || []} /></Row>
    <Row label="학력"><Select label="학력" value={conditions.education} onChange={(education) => onChange({ education })} options={meta?.schools || []} /></Row>
    <Row label="거주지역"><Select label="거주지역" value={conditions.region} onChange={(region) => onChange({ region })} options={(meta?.sido || []).map(({ code, name }) => ({ value: code, label: name }))} /></Row>
    <label className="checkbox"><input type="checkbox" checked={conditions.include_nationwide} disabled={!conditions.region} onChange={(event) => onChange({ include_nationwide: event.target.checked })} />전국 정책도 보기</label>
    <label className="checkbox"><input type="checkbox" checked={conditions.include_closed} onChange={(event) => onChange({ include_closed: event.target.checked })} />마감된 정책도 보기</label>
    <button className="button-ghost" onClick={onReset} disabled={!dirty}>조건 지우기</button>
    <p className="box-note">자격 제한이 없는 정책은 조건과 상관없이 늘 나와요. 지역을 고르면 전국 정책은 기본적으로 빼서 지역 차이를 보여드려요.</p>
  </div></aside>
}

function Row({ label, children }) { return <div className="row"><span className="row-label">{label}</span>{children}</div> }

// 청년정책 서비스라 청년 범위 밖 나이는 받지 않는다. number input 의 min/max 는
// 스피너만 제한하고 직접 타이핑은 막지 못해서, 값이 벗어나면 조건에서 빼고
// 왜 뺐는지 알려준다. 백엔드 UserProfile 도 같은 범위로 검증한다.
const YOUTH_MIN_AGE = 15
const YOUTH_MAX_AGE = 49

function AgeField({ value, onChange }) {
  const typed = String(value ?? '').trim()
  const number = Number(typed)
  const outOfRange = typed !== '' && Number.isFinite(number) && (number < YOUTH_MIN_AGE || number > YOUTH_MAX_AGE)

  return <>
    <div className="age-row">
      <input
        aria-label="나이"
        aria-invalid={outOfRange || undefined}
        type="number"
        min={YOUTH_MIN_AGE}
        max={YOUTH_MAX_AGE}
        className={`input age-input${outOfRange ? ' is-invalid' : ''}`}
        value={value}
        placeholder="나이"
        onChange={(event) => onChange(event.target.value)}
      />
      <span className="unit">세</span>
    </div>
    {outOfRange && <p className="field-error" role="alert">
      청년정책은 {YOUTH_MIN_AGE}~{YOUTH_MAX_AGE}세를 대상으로 해요. 이 나이는 조건에서 빼고 찾을게요.
    </p>}
  </>
}
function Select({ label, value, onChange, options }) {
  const items = options.map((item) => typeof item === 'string' ? { value: item, label: item } : item)
  return <select aria-label={label} className="input" value={value} onChange={(event) => onChange(event.target.value)}><option value="">선택 안 함</option>{items.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
}
