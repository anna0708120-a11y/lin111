import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.life.interpretations import (
    derive_interpretations,
    format_interpretations_for_prompt,
    relevant_interpretations,
)


class LifeInterpretationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)

    def event(self, event_type, minutes_ago, payload=None, confidence=0.95):
        occurred_at = self.now - timedelta(minutes=minutes_ago)
        return {
            "event_id": f"{event_type}:{minutes_ago}",
            "event_type": event_type,
            "occurred_at": occurred_at.isoformat().replace("+00:00", "Z"),
            "payload": payload or {},
            "confidence": confidence,
        }

    def test_multiple_recent_observations_create_bounded_workload_focus_hypothesis(self):
        items = derive_interpretations([
            self.event("mac.active", 25, {"to": "active"}),
            self.event("mac.unlocked", 15, {"to": "active"}),
            self.event("screentime.summary", 10, {"activity": "high", "total_minutes": 420}),
        ], now=self.now)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["kind"], "workload.focus")
        self.assertIn("可能", item["hypothesis"])
        self.assertGreaterEqual(len(item["evidence"]), 2)
        self.assertGreater(item["confidence"], 0)
        self.assertGreater(item["expires_at"], item["observed_at"])

    def test_single_mac_observation_does_not_create_workload_hypothesis(self):
        items = derive_interpretations([self.event("mac.active", 10, {"to": "active"})], now=self.now)
        self.assertEqual(items, [])

    def test_stale_evidence_does_not_create_workload_hypothesis(self):
        items = derive_interpretations([
            self.event("mac.active", 300, {"to": "active"}),
            self.event("mac.unlocked", 280, {"to": "active"}),
            self.event("screentime.summary", 270, {"activity": "high"}),
        ], now=self.now)
        self.assertEqual(items, [])

    def test_only_relevant_conversation_receives_interpretation(self):
        item = derive_interpretations([
            self.event("mac.active", 25, {"to": "active"}),
            self.event("mac.unlocked", 15, {"to": "active"}),
            self.event("screentime.summary", 10, {"activity": "high"}),
        ], now=self.now)
        self.assertEqual(len(relevant_interpretations(item, "你最近的项目怎么样？")), 1)
        self.assertEqual(relevant_interpretations(item, "今天的电影很好看"), [])

    def test_prompt_renderer_keeps_observation_and_hypothesis_distinct(self):
        item = derive_interpretations([
            self.event("mac.active", 25, {"to": "active"}),
            self.event("mac.unlocked", 15, {"to": "active"}),
            self.event("screentime.summary", 10, {"activity": "high"}),
        ], now=self.now)
        prompt = format_interpretations_for_prompt(item)
        self.assertIn("观察", prompt)
        self.assertIn("推测", prompt)
        self.assertIn("不要把推测当成事实", prompt)

    @patch("app.life.interpretations.db")
    def test_derivation_does_not_write_or_query_database(self, db):
        derive_interpretations([
            self.event("mac.active", 25, {"to": "active"}),
            self.event("mac.unlocked", 15, {"to": "active"}),
            self.event("screentime.summary", 10, {"activity": "high"}),
        ], now=self.now)
        db.assert_not_called()


if __name__ == "__main__":
    unittest.main()
