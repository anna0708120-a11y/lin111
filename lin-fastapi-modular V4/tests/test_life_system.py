"""Phase 6 Life System tests: no database, LLM, or network required."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app.life.contracts import LifeEvent, LifeState, iso_utc
from app.life.event_normalizer import (
    normalize_calendar,
    normalize_conversation,
    normalize_location,
    normalize_mac,
    normalize_screentime,
)
from app.life.runtime import get_life_context, get_life_state, get_timeline, ingest_events, replay_events
from app.life.state_engine import apply_event, mark_conversation_idle


class LifeSystemTests(unittest.TestCase):
    def test_location_transitions_and_unknown_baseline(self):
        first = normalize_location({"label": "home", "timestamp": "2026-08-10T08:20:00+08:00"}, "unknown")
        self.assertEqual(first[0].event_type, "location.returned_home")
        state, changed = apply_event(LifeState(), first[0])
        self.assertEqual(state.location_state, "at_home")
        self.assertEqual(changed, ["location_state"])

        left = normalize_location({"label": "office", "timestamp": "2026-08-10T09:10:00+08:00"}, state.location_state)
        state, _ = apply_event(state, left[0])
        self.assertEqual(left[0].event_type, "location.left_home")
        self.assertEqual(state.location_state, "outside")

        returned = normalize_location({"label": "home", "timestamp": "2026-08-10T18:40:00+08:00"}, state.location_state)
        state, _ = apply_event(state, returned[0])
        self.assertEqual(state.location_state, "at_home")

    def test_mac_active_idle_and_charging(self):
        active = normalize_mac({"locked": False, "charging": False, "timestamp": "2026-08-10T13:20:00Z"}, "idle")
        self.assertEqual(active[0].event_type, "mac.active")
        state = LifeState(mac_state="idle")
        for event in active:
            state, _ = apply_event(state, event)
        self.assertEqual(state.mac_state, "active")
        self.assertFalse(state.mac_charging)

        idle = normalize_mac({"asleep": True, "timestamp": "2026-08-10T14:20:00Z"}, state.mac_state)
        state, _ = apply_event(state, idle[0])
        self.assertEqual(state.mac_state, "idle")

    def test_calendar_and_conversation_state(self):
        event = normalize_calendar([{"title": "meeting", "start": "2026-08-11 10:00", "end": "2026-08-11 11:00"}])[0]
        state, _ = apply_event(LifeState(), event)
        self.assertEqual(state.next_schedule["title"], "meeting")

        message = normalize_conversation("anna", "I am home", session_id="s1", occurred_at="2026-08-10T22:30:00+08:00")[0]
        state, changed = apply_event(state, message)
        self.assertEqual(state.conversation_state, "active")
        self.assertIn("last_user_activity_at", changed)

        idle, changed = mark_conversation_idle(state, datetime(2026, 8, 10, 16, 30, tzinfo=timezone.utc), threshold_minutes=90)
        self.assertEqual(idle.conversation_state, "idle")
        self.assertEqual(changed, ["conversation_state"])

    def test_screentime_dedupes_same_daily_total(self):
        self.assertEqual(normalize_screentime({"total_minutes": 120, "date": "2026-08-10"}, 120), [])
        event = normalize_screentime({"total_minutes": 121, "date": "2026-08-10"}, 120)[0]
        self.assertEqual(event.event_type, "screentime.summary")
        self.assertEqual(event.payload["activity"], "moderate")

    def test_replay_is_deterministic_and_duplicate_ingest_is_idempotent(self):
        events = []
        events += normalize_location({"label": "home", "timestamp": "2026-08-10T08:20:00+08:00"}, "unknown")
        events += normalize_location({"label": "office", "timestamp": "2026-08-10T09:10:00+08:00"}, "at_home")
        events += normalize_location({"label": "home", "timestamp": "2026-08-10T18:40:00+08:00"}, "outside")
        expected = replay_events(events)
        self.assertEqual(expected.location_state, "at_home")

        first = ingest_events(events)
        second = ingest_events(events)
        self.assertTrue(any(row["inserted"] for row in first))
        self.assertTrue(all(not row["inserted"] for row in second))
        self.assertEqual(get_life_state()["location_state"], "at_home")
        timeline = get_timeline("2026-08-10")
        self.assertGreaterEqual(len(timeline), 3)
        context = get_life_context()
        self.assertEqual(context["state"]["location_state"], "at_home")

    def test_timezone_normalization(self):
        value = iso_utc("2026-08-10T08:20:00+08:00")
        self.assertEqual(value, "2026-08-10T00:20:00Z")


if __name__ == "__main__":
    unittest.main()
