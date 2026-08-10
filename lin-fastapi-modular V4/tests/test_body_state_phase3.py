import asyncio
import json
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from app.intimacy.after_effect import AfterEffect
from app.intimacy.body_state import calculate_body_state
from app.intimacy.settlement import apply_settlement_result, build_settlement_result
from app.intimacy.status import build_intimacy_status_payload
from app.intimacy.tick import _finish_event, start_event
from app.web.routes import Activity, observe_anna


class EventAndSettlementTests(unittest.TestCase):
    def test_start_event_logs_and_sets_live_event_state(self):
        now = datetime(2026, 8, 6, 12, 0, 0)
        state = SimpleNamespace(
            active_event_key=None,
            active_event_started_at=None,
            active_event_expires_at=None,
            save_body_state=lambda: None,
        )
        with patch("app.intimacy.event_log.log_event") as log_event:
            self.assertTrue(start_event(state, "low_fever_cling", now))

        self.assertEqual(state.active_event_key, "low_fever_cling")
        self.assertEqual(state.active_event_started_at, now)
        self.assertGreater(state.active_event_expires_at, now)
        log_event.assert_called_once()
        metadata = log_event.call_args.kwargs["metadata"]
        self.assertEqual(metadata["phase"], "started")
        self.assertEqual(metadata["body_state"]["active_event_key"], "low_fever_cling")

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

    def test_status_payload_prefers_after_effect_when_event_is_inactive(self):
        now = datetime(2026, 8, 6, 12, 0, 0)
        state = SimpleNamespace(
            mood={},
            body_values={"tension": 30, "heat": 30, "sensitivity": 30, "control": 70},
            cycle_key="stable",
            cycle_started_at=now,
            cycle_expires_at=now + timedelta(hours=72),
            active_event_key=None,
            active_event_started_at=None,
            active_event_expires_at=None,
            active_after_effects=[AfterEffect(
                "post_waiting", 30, {"tension": 2}, "等待後的餘溫", now, now + timedelta(minutes=15)
            )],
            last_tick_at=now,
        )

        payload = build_intimacy_status_payload(state, now)

        self.assertIsNone(payload["active_event"])
        self.assertEqual(payload["after_effects"][0]["remaining_text"], "剩 15m")

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

    def test_waiting_gap_starts_a_new_continuous_turn_streak(self):
        now = datetime(2026, 8, 6, 12, 0, 0)
        previous_message_at = now - timedelta(minutes=11)
        continuous_turns = 3

        next_turns = continuous_turns + 1 if (now - previous_message_at).total_seconds() < 10 * 60 else 1

        self.assertEqual(next_turns, 1)

    def test_mood_mapping_adjusts_targets_without_overriding_cycle(self):
        cycle = SimpleNamespace(
            targets={"tension": 20, "heat": 30, "sensitivity": 25, "control": 80},
            growth_rates={"tension": 1, "heat": 1, "sensitivity": 1, "control": -1},
        )
        current = {"tension": 20, "heat": 30, "sensitivity": 25, "control": 80}
        baseline = calculate_body_state({}, cycle, current, 1)
        adjusted = calculate_body_state(
            {"libido": 0.5, "attachment": 0.9, "possessiveness": 0.9, "stress": 0.2, "fatigue": 0.1},
            cycle,
            current,
            1,
        )

        self.assertGreater(adjusted["tension"], baseline["tension"])
        self.assertGreater(adjusted["heat"], baseline["heat"])
        self.assertGreater(adjusted["sensitivity"], baseline["sensitivity"])
        self.assertLess(adjusted["control"], 100)


class WatchSseTests(unittest.TestCase):
    def test_watch_stream_emits_content_body_state_and_done(self):
        import app.llm.deepseek_client as deepseek_client
        from app.web import routes

        def fake_stream(*_args, **_kwargs):
            yield "content", "測試回覆"
            yield "raw_reasoning", ""
            yield "done", None

        original_stream = deepseek_client.call_deepseek_stream
        original_rate_limit = routes.state.check_rate_limit
        original_record_call = routes.state.record_call
        original_add_log = routes.state.add_log
        original_add_turn = routes.state.add_conversation_turn
        original_mark_anchor = routes.state.mark_conversation_anchor
        original_save_body = routes.state.save_body_state
        original_send_to_bark = None
        try:
            deepseek_client.call_deepseek_stream = fake_stream
            routes.state.check_rate_limit = lambda: True
            routes.state.record_call = lambda: None
            routes.state.add_log = lambda *_args, **_kwargs: None
            routes.state.add_conversation_turn = lambda *_args, **_kwargs: None
            routes.state.mark_conversation_anchor = lambda: None
            routes.state.save_body_state = lambda: None

            import app.notify.bark as bark
            original_send_to_bark = bark.send_to_bark
            bark.send_to_bark = lambda *_args, **_kwargs: None

            response = observe_anna(Activity(activity="謝謝你"))

            async def collect():
                chunks = []
                async for chunk in response.body_iterator:
                    chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
                return "".join(chunks)

            payload = asyncio.run(collect())
        finally:
            deepseek_client.call_deepseek_stream = original_stream
            routes.state.check_rate_limit = original_rate_limit
            routes.state.record_call = original_record_call
            routes.state.add_log = original_add_log
            routes.state.add_conversation_turn = original_add_turn
            routes.state.mark_conversation_anchor = original_mark_anchor
            routes.state.save_body_state = original_save_body
            if original_send_to_bark is not None:
                bark.send_to_bark = original_send_to_bark

        self.assertIn("event: content", payload)
        self.assertIn("event: body_state", payload)
        self.assertIn("event: done", payload)
        body_data = payload.split("event: body_state\ndata: ", 1)[1].split("\n\n", 1)[0]
        rendered = json.loads(body_data)
        self.assertIn("body_values", rendered)
        self.assertIn("cycle", rendered)
        self.assertIn("after_effects", rendered)


if __name__ == "__main__":
    unittest.main()
