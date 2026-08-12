import unittest
from unittest.mock import Mock, patch

from app.life.gemma_interpreter import interpret_life_evidence


class GemmaLifeInterpreterTests(unittest.TestCase):
    @patch("app.life.gemma_interpreter.requests.post")
    @patch("app.life.gemma_interpreter.config.GEMMA_MODEL", "gemma4:31b")
    @patch("app.life.gemma_interpreter.config.GEMMA_API_KEY", "test-key")
    def test_gemma_returns_bounded_observation_and_hypothesis(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"message": {"content": '{"observation":"下午有持续电脑活动。","interpretation":"Anna可能在处理项目。","evidence_sufficient":true,"relevance_terms":["项目","电脑"],"confidence":0.6}'}}
        post.return_value = response
        result = interpret_life_evidence([
            {"event_id": "m1", "event_type": "mac.active", "occurred_at": "2026-08-11T10:00:00Z", "confidence": 0.95, "payload": {"to": "active"}},
            {"event_id": "c1", "event_type": "calendar.upcoming", "occurred_at": "2026-08-11T10:05:00Z", "confidence": 0.9, "payload": {"title": "project"}},
        ])
        self.assertEqual(result["observation"], "下午有持续电脑活动。")
        self.assertIn("可能", result["interpretation"])
        self.assertEqual(result["relevance_terms"], ["项目", "电脑"])
        self.assertEqual(post.call_args.args[0], "https://ollama.com/api/chat")

    @patch("app.life.gemma_interpreter.config.GEMMA_API_KEY", "")
    def test_missing_gemma_returns_no_interpretation(self):
        self.assertIsNone(interpret_life_evidence([]))


if __name__ == "__main__":
    unittest.main()
