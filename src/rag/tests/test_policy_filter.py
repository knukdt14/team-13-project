import unittest
from datetime import date

from src.rag.eligibility import PolicyFilter


class PolicyFilterTest(unittest.TestCase):
    def setUp(self):
        self.filter = PolicyFilter(today=date(2026, 8, 4))
        self.policy = {
            "sprtTrgtAgeLmtYn": "Y",
            "sprtTrgtMinAge": "19",
            "sprtTrgtMaxAge": "34",
            "zipCdList": ["27110"],
            "jobCdNmList": ["미취업자"],
            "schoolCdNmList": ["제한없음"],
            "mrgSttsCdNm": "제한없음",
            "lclsfNm": "주거",
            "mclsfNm": "주거비지원",
            "plcyKywdNm": "월세",
            "aplyPrdSeCdNm": "특정기간",
            "aplyStartYmd": "2026-08-01",
            "aplyEndYmd": "2026-08-31",
        }

    def test_matches_all_hard_filters(self):
        conditions = {"age": 28, "region": "대구", "employment": "미취업자"}
        self.assertTrue(self.filter.matches(self.policy, conditions))

    def test_rejects_age_outside_range(self):
        self.assertFalse(self.filter.matches(self.policy, {"age": 40}))

    def test_rejects_other_region(self):
        self.assertFalse(self.filter.matches(self.policy, {"region": "서울"}))

    def test_rejects_closed_policy_by_default(self):
        self.policy["aplyEndYmd"] = "2026-08-03"
        self.assertFalse(self.filter.matches(self.policy, {}))
        self.assertTrue(self.filter.matches(self.policy, {}, include_closed=True))

    def test_uses_local_provider_when_zip_codes_are_wrongly_nationwide(self):
        self.policy["zipCdList"] = ["11110", "12110", "26110", "27110", "28125"]
        self.policy["rgtrInstCdNm"] = "전라남도 광양시 미래산업국"
        self.assertFalse(self.filter.matches(self.policy, {"region": "대구"}))
        self.assertTrue(self.filter.matches(self.policy, {"region": "전남"}))

    def test_income_bracket_uses_explicit_median_income_threshold(self):
        self.policy["earnCndSeCdNm"] = "기타"
        self.policy["earnEtcCn"] = "기준 중위소득 120% 이하"
        self.assertTrue(self.filter.matches(self.policy, {"income_bracket": 100}))
        self.assertFalse(self.filter.matches(self.policy, {"income_bracket": 150}))


if __name__ == "__main__":
    unittest.main()
