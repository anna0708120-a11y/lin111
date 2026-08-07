import unittest
from unittest.mock import patch

from app.memory_intent import build_memory_decision, detect_memory_intent


class MemoryIntentTests(unittest.TestCase):
    def test_detects_explicit_remember_request(self):
        self.assertEqual(
            detect_memory_intent("Anna说：记住我喜欢狗"),
            {"explicit": True, "fact": "喜欢狗", "source": "Anna说：记住我喜欢狗"},
        )

    def test_detects_traditional_explicit_remember_request(self):
        self.assertTrue(detect_memory_intent("請記住我喜歡狗")["explicit"])

    @patch("app.memory_intent.call_deepseek")
    def test_explicit_request_builds_create_decision_without_memory_tag(self, mock_call):
        mock_call.return_value = ('{"tag":"喜好","keyword":"喜欢狗","summary":"Anna喜欢狗"}', None)
        self.assertEqual(
            build_memory_decision("Anna说：记住我喜欢狗"),
            {
                "action": "create",
                "importance": 3,
                "category": "长期记忆",
                "tag": "喜好",
                "keyword": "喜欢狗",
                "summary": "Anna喜欢狗",
            },
        )
        prompt = mock_call.call_args.args[0]
        self.assertIn("只输出 JSON", prompt)
        self.assertNotIn("MEMORY_DECISION", prompt)

    @patch("app.memory_intent.call_deepseek", return_value=(None, None))
    def test_explicit_request_keeps_writer_safe_fallback_when_field_call_fails(self, _mock_call):
        decision = build_memory_decision("请记住我喜欢狗")
        self.assertEqual(decision["action"], "create")
        self.assertEqual(decision["importance"], 3)
        self.assertEqual(decision["summary"], "喜欢狗")


if __name__ == "__main__":
    unittest.main()
