import unittest

from src.rag.interpreter import (
    INTENT_CHAT,
    INTENT_FOLLOW_UP,
    INTENT_SEARCH,
    parse_interpretation,
)


class ConversationInterpretationTest(unittest.TestCase):
    def test_parses_general_chat(self):
        result = parse_interpretation(
            '{"intent":"chat","standalone_question":"안녕","policy_ids":[],"conditions":{}}',
            "안녕",
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.intent, INTENT_CHAT)
        self.assertEqual(result.standalone_question, "안녕")

    def test_parses_follow_up_with_known_policy(self):
        result = parse_interpretation(
            """{
                "intent": "follow_up",
                "standalone_question": "청년 월세지원 정책의 신청 방법은?",
                "policy_ids": ["정책123"],
                "conditions": {}
            }""",
            "3번 정책은 어떻게 신청해?",
            ["정책123"],
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.intent, INTENT_FOLLOW_UP)
        self.assertEqual(result.policy_ids, ["정책123"])

    def test_unknown_follow_up_policy_falls_back_to_search(self):
        result = parse_interpretation(
            """{
                "intent": "follow_up",
                "standalone_question": "알 수 없는 정책의 신청 방법은?",
                "policy_ids": ["없는정책"],
                "conditions": {}
            }""",
            "그 정책은 어떻게 신청해?",
            ["정책123"],
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.intent, INTENT_SEARCH)
        self.assertEqual(result.policy_ids, [])

    def test_invalid_response_uses_safe_fallback(self):
        question = "대구 창업 정책을 알려줘"
        result = parse_interpretation("JSON이 아닌 응답", question)

        self.assertFalse(result.ok)
        self.assertEqual(result.intent, INTENT_SEARCH)
        self.assertEqual(result.standalone_question, question)


if __name__ == "__main__":
    unittest.main()
