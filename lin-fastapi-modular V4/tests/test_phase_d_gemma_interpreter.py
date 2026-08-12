import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from app.life import gemma_interpreter


class GemmaLifeInterpreterPhaseDTests(unittest.TestCase):
    def setUp(self):
        gemma_interpreter._CACHE.update({"expires_at": 0.0, "value": None})

    @patch("app.life.gemma_interpreter.requests.post")
    @patch("app.life.gemma_interpreter.config.GEMMA_MODEL", "gemma4:31b")
    @patch("app.life.gemma_interpreter.config.GEMMA_API_KEY", "test-key")
    def test_interpretation_preserves_evidence_and_expiry(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"message": {"content": '{"observation":"two work observations","interpretation":"Anna may be focused","evidence_sufficient":true,"confidence":0.7,"relevance_terms":["工作"]}'}}
        post.return_value = response
        result = gemma_interpreter.interpret_life_evidence([
            {"event_id":"m1","event_type":"mac.active","occurred_at":"2026-08-12T10:00:00Z","confidence":0.95,"payload":{}},
            {"event_id":"c1","event_type":"calendar.upcoming","occurred_at":"2026-08-12T10:05:00Z","confidence":0.9,"payload":{"title":"project"}},
        ])
        self.assertEqual([item["event_id"] for item in result["evidence"]], ["m1", "c1"])
        self.assertTrue(result["evidence_sufficient"])
        self.assertGreater(result["expires_at"], result["observed_at"])
        self.assertLessEqual(result["confidence"], 0.8)

    @patch("app.life.gemma_interpreter.requests.post")
    @patch("app.life.gemma_interpreter.config.GEMMA_MODEL", "gemma4:31b")
    @patch("app.life.gemma_interpreter.config.GEMMA_API_KEY", "test-key")
    def test_insufficient_evidence_does_not_produce_interpretation(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"message": {"content": '{"observation":"one event","interpretation":"Anna is working","evidence_sufficient":false,"confidence":0.9,"relevance_terms":["工作"]}'}}
        post.return_value = response
        result = gemma_interpreter.interpret_life_evidence([
            {"event_id":"m1","event_type":"mac.active","occurred_at":"2026-08-12T10:00:00Z","confidence":0.95,"payload":{}}
        ])
        self.assertIsNone(result)

    @patch("app.life.gemma_interpreter.requests.post")
    @patch("app.life.gemma_interpreter.config.GEMMA_MODEL", "gemma4:31b")
    @patch("app.life.gemma_interpreter.config.GEMMA_API_KEY", "test-key")
    def test_irrelevant_conversation_isolated(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"message": {"content": '{"observation":"obs","interpretation":"hypothesis","evidence_sufficient":true,"confidence":0.6,"relevance_terms":["工作"]}'}}
        post.return_value = response
        value = gemma_interpreter.interpret_life_evidence([
            {"event_id":"m1","event_type":"mac.active","occurred_at":"2026-08-12T10:00:00Z","confidence":0.95,"payload":{}},
            {"event_id":"c1","event_type":"calendar.upcoming","occurred_at":"2026-08-12T10:05:00Z","confidence":0.9,"payload":{}}
        ])
        self.assertIsNone(gemma_interpreter.relevant_life_interpretation(value, "今晚吃什么？"))
        self.assertIsNotNone(gemma_interpreter.relevant_life_interpretation(value, "工作進度如何？"))


if __name__ == "__main__":
    unittest.main()
