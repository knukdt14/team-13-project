const POLICY = {
  plcy_no: 'mock-001', title: '청년 주거비 지원사업', organization: '청년지원센터',
  categories: ['주거'], age_label: '19–34세', period_label: '상시 모집', days_left: null,
  status: '상시', jobs: ['제한없음'], schools: ['제한없음'], regions: ['전국'],
  summary: '청년의 주거비 부담을 덜어주는 정책이에요.', apply_url: '#',
  application_url: '#', reference_url: '#policy', can_apply_directly: true,
}

const wait = (value) => new Promise((resolve) => setTimeout(() => resolve(value), 180))

export function respond(path, options = {}) {
  if (path.startsWith('/meta')) return wait({
    total: 2693, jobs: ['재직자', '미취업자', '(예비)창업자'],
    schools: ['고교 졸업', '대학 재학', '대학 졸업'],
    sido: [{ code: '27', name: '대구광역시' }, { code: '47', name: '경상북도' }],
  })
  if (path.startsWith('/policies')) return wait({ total: 2693, matched: 1, page: 1, size: 20, items: [POLICY] })
  if (path.startsWith('/regions/summary')) return wait({
    matched: 42, max: 18, nationwide: 12,
    regions: [{ code: '27', name: '대구광역시', count: 8 }, { code: '47', name: '경상북도', count: 18 }],
  })
  if (path.startsWith('/documents') && options.method === 'POST') return wait({ items: [] })
  if (path.startsWith('/documents')) return wait([])
  if (path.startsWith('/sessions/')) return wait([])
  if (path === '/ask') return wait({
    answer: '조건에 맞는 정책을 찾아봤어요.', sources: [{
      plcy_no: POLICY.plcy_no, title: POLICY.title, organization: POLICY.organization,
      category: '주거', snippet: POLICY.summary, score: 1, policy: POLICY,
    }], matched_policies: [POLICY.plcy_no], session_id: 'mock', elapsed_ms: 180,
    matched: 1, total: 2693, relevant: true, generated: false, used_attachments: false,
  })
  return wait({})
}
