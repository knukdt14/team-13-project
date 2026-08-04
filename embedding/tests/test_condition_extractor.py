import unittest

from embedding.condition_extractor import ConditionExtractor


class ConditionExtractorTest(unittest.TestCase):
    def setUp(self):
        self.extractor = ConditionExtractor()

    def test_extracts_common_conditions(self):
        conditions, search_text = self.extractor.extract(
            "대구에 사는 28살 미취업자인데 받을 수 있는 주거 지원 정책 알려줘"
        )
        self.assertEqual(conditions.age, 28)
        self.assertEqual(conditions.region, "대구")
        self.assertEqual(conditions.employment, "미취업자")
        self.assertEqual(conditions.category, "주거")
        self.assertIn("지원", search_text)

    def test_extracts_school_and_marriage(self):
        conditions, _ = self.extractor.extract("서울 거주 미혼 대학생이 신청할 장학금")
        self.assertEqual(conditions.region, "서울")
        self.assertEqual(conditions.education, "대학 재학")
        self.assertEqual(conditions.marriage, "미혼")

    def test_extracts_income_bracket(self):
        conditions, _ = self.extractor.extract("중위소득 120%인 부산 대학생 장학금")
        self.assertEqual(conditions.income_bracket, 120)
        self.assertEqual(conditions.region, "부산")
        self.assertEqual(conditions.education, "대학 재학")


if __name__ == "__main__":
    unittest.main()
