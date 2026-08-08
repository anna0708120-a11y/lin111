import unittest

from app.memory_intent import build_memory_decision, detect_memory_intent


class MemoryIntentTests(unittest.TestCase):
    def test_detects_explicit_remember_request(self):
        self.assertEqual(
            detect_memory_intent("Anna说：记住我喜欢狗"),
            {"explicit": True, "fact": "喜欢狗", "source": "Anna说：记住我喜欢狗"},
        )

    def test_detects_traditional_explicit_remember_request(self):
        self.assertTrue(detect_memory_intent("請記住我喜歡狗")["explicit"])

    def test_detects_dont_forget_request(self):
        self.assertEqual(
            detect_memory_intent("以后不要忘记我喜欢狗"),
            {"explicit": True, "fact": "喜欢狗", "source": "以后不要忘记我喜欢狗"},
        )

    def test_explicit_request_builds_existing_create_decision(self):
        self.assertEqual(
            build_memory_decision("Anna说：记住我喜欢狗"),
            {
                "action": "create",
                "importance": 3,
                "category": "长期记忆",
                "tag": "用户明确要求",
                "keyword": "喜欢狗",
                "summary": "喜欢狗",
            },
        )

    def test_regular_chat_does_not_create_a_backend_decision(self):
        self.assertIsNone(build_memory_decision("我喜欢狗"))


if __name__ == "__main__":
    unittest.main()
