import unittest

from src.rag.prompts import is_greeting, is_personalized_request


class ConversationIntentTest(unittest.TestCase):
    def test_short_greeting_does_not_need_policy_search(self):
        self.assertTrue(is_greeting("안녕"))
        self.assertTrue(is_greeting("안녕하세요!"))
        self.assertFalse(is_greeting("안녕하세요, 창업 정책을 알려줘"))

    def test_detects_personalized_policy_request(self):
        self.assertTrue(is_personalized_request("나에게 가장 관련된 정책을 찾아줘"))
        self.assertTrue(is_personalized_request("내게 맞는 정책이 있어?"))
        self.assertFalse(is_personalized_request("대구 창업 정책을 알려줘"))


if __name__ == "__main__":
    unittest.main()
