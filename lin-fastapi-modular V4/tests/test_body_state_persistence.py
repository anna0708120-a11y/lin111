"""Regression tests for Body State current-snapshot persistence.

These tests use the existing app_state key-value contract in memory. They do not
require Supabase and do not create production history records or tables.
"""
import unittest
from datetime import datetime, timedelta

from app import state as state_module
from app.intimacy.after_effect import AfterEffect
from app.intimacy.tick import tick_and_update


class BodyStatePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.store = {}
        self.original_load = state_module.db.load_state_value
        self.original_save = state_module.db.save_state_value
        state_module.db.load_state_value = lambda key, default=None: self.store.get(key, default)
        state_module.db.save_state_value = lambda key, value: self.store.__setitem__(key, value)

    def tearDown(self):
        state_module.db.load_state_value = self.original_load
        state_module.db.save_state_value = self.original_save

    def test_snapshot_round_trip_restores_runtime_fields(self):
        first = state_module.AppState()
        now = datetime(2026, 8, 6, 12, 0, 0)
        first.body_values = {
            "tension": 61.5,
            "heat": 48.2,
            "sensitivity": 55.0,
            "control": 42.3,
        }
        first.cycle_key = "preheat"
        first.cycle_started_at = now - timedelta(hours=4)
        first.cycle_expires_at = now + timedelta(hours=20)
        first.last_tick_at = now
        first.active_event_key = "low_fever_cling"
        first.active_event_started_at = now - timedelta(minutes=10)
        first.active_event_expires_at = now + timedelta(minutes=35)
        first.last_user_message_at = now - timedelta(minutes=2)
        first.continuous_turns = 4
        first.active_after_effects = [
            AfterEffect(
                source_event="post_waiting",
                duration_minutes=30,
                deltas_per_hour={"tension": 2},
                description="test",
                started_at=now,
                expires_at=now + timedelta(minutes=30),
            )
        ]
        first.save_body_state()

        restarted = state_module.AppState()

        self.assertEqual(restarted.body_values, first.body_values)
        self.assertEqual(restarted.cycle_key, "preheat")
        self.assertEqual(restarted.cycle_started_at, first.cycle_started_at)
        self.assertEqual(restarted.cycle_expires_at, first.cycle_expires_at)
        self.assertEqual(restarted.last_tick_at, now)
        self.assertEqual(restarted.active_event_key, "low_fever_cling")
        self.assertEqual(restarted.active_event_expires_at, first.active_event_expires_at)
        self.assertEqual(restarted.continuous_turns, 4)
        self.assertEqual(len(restarted.active_after_effects), 1)
        self.assertEqual(restarted.active_after_effects[0].source_event, "post_waiting")

    def test_same_timestamp_tick_is_idempotent_after_restart(self):
        state = state_module.AppState()
        now = datetime(2026, 8, 6, 12, 0, 0)
        tick_and_update(state, now)
        before = dict(state.body_values)
        snapshot_before = dict(self.store["body_state"])

        tick_and_update(state, now)

        self.assertEqual(state.body_values, before)
        self.assertEqual(state.last_tick_at, now)
        self.assertEqual(self.store["body_state"], snapshot_before)


if __name__ == "__main__":
    unittest.main()
