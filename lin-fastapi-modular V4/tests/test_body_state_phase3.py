"""Regression tests for Phase 3 current Event/Settlement integration."""
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.intimacy.after_effect import AfterEffect
from app.intimacy.settlement import (
    apply_settlement_result,
    build_settlement_result,
)
from app.intimacy.status import build_intimacy_status_payload
from app.intimacy.tick import _finish_event


class EventAndSettlementTests(unittest.TestCase):
    def test_status_payload_uses_live_cycle_event_and_after_effect(self):
        now = datetime(2026, 8, 6, 12, 0, 0)
        state = SimpleNamespace(
            mood={"attachment": 0.6, "possessiveness": 0.4, "stress": 0.2, "fatigue": 0.2},
            body_values={"tension": 50, "heat": 45, "sensitivity": 40, "control": 60},
            cycle_key="preheat",
            cycle_started_at=now - timedelta(hours=2),
            cycle_expires_at=now + timedelta(hours=8),
            active_event_key="low_fever_cling",
            active_event_started_at=now - timedelta(minutes=5),
            active_event_expires_at=now + timedelta(minutes=25),
            active_after_effects=[AfterEffect(
                "post_waiting", 30, {"tension": 2}, "等待後的餘溫", now, now + timedelta(minutes=15)
            )],
            last_tick_at=now,
        )

        payload = build_intimacy_status_payload(state, now)

        self.assertEqual(payload["cycle"]["key"], "preheat")
        self.assertEqual(payload["cycle"]["remaining_seconds"], 8 * 3600)
        self.assertEqual(payload["active_event"]["key"], "low_fever_cling")
        self.assertEqual(payload["active_event"]["remaining_seconds"], 25 * 60)
        self.assertEqual(payload["after_effects"][0]["source_event"], "post_waiting")

    def test_event_finish_clears_active_event_and_keeps_after_effect(self):
        now = datetime(2026, 8, 6, 12, 0, 0)
        state = SimpleNamespace(
            body_values={"tension": 60, "heat": 50, "sensitivity": 45, "control": 65},
            active_event_key="waiting_restless",
            active_event_started_at=now - timedelta(minutes=60),
            active_event_expires_at=now,
            active_after_effects=[],
        )

        _finish_event(state, now)

        self.assertIsNone(state.active_event_key)
        self.assertIsNone(state.active_event_expires_at)
        self.assertEqual(len(state.active_after_effects), 1)
        self.assertEqual(state.active_after_effects[0].source_event, "post_waiting")

    def test_settlement_is_bounded_and_never_uses_release(self):
        state = SimpleNamespace(body_values={"tension": 50, "heat": 50, "sensitivity": 50, "control": 50})
        result = build_settlement_result("我好生氣，不想說了", "我知道，你先別逼自己。", 2)
        applied = apply_settlement_result(state, result)

        self.assertEqual(applied["result"], "argument")
        self.assertEqual(applied["applied_deltas"]["tension"], 3.0)
        self.assertGreaterEqual(state.body_values["control"], 0)
        self.assertNotIn("release", applied["result"])


if __name__ == "__main__":
    unittest.main()
