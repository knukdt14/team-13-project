import PolicyCard from './PolicyCard'

export default function PolicyCardList({ policies = [] }) {
  return <ul className="policy-cards">{policies.map((policy) => <PolicyCard key={policy.plcy_no} policy={policy} />)}</ul>
}
