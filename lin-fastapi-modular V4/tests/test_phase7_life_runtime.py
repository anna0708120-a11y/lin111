"""Phase 7 lifecycle tests without Supabase or network."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.life import LifeEvent, evaluate_candidate, execute_candidate, ingest_events, reset_memory_runtime
from app.life import outbox
from app.life.phase7 import get_audit, get_candidate
from app.life.policy import PolicyConfig, evaluate
from app.life.candidates import build

NO_QUIET_HOURS = PolicyConfig(quiet_start_hour=24, quiet_end_hour=25)


class Phase7Tests(unittest.TestCase):
    def setUp(self):
        reset_memory_runtime()
        outbox.reset_memory_outbox()

    def event(self, event_type: str, event_id: str, payload=None):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        return LifeEvent(event_id, event_type, "test", now, now, payload or {}, 1.0, f"test:{event_id}")

    def candidate_for(self, event: LifeEvent):
        result = ingest_events([event])
        candidate_id = f"candidate_{__import__('hashlib').sha256(f'{event.event_id}:{'welcome_home' if event.event_type == 'location.returned_home' else 'conversation_followup'}'.encode()).hexdigest()[:24]}"
        candidate = get_candidate(candidate_id)
        self.assertIsNotNone(candidate)
        return result, candidate

    def test_return_home_candidate_policy_prepare_and_audit(self):
        _, candidate = self.candidate_for(self.event("location.returned_home", "evt-home", {"from": "outside", "to": "at_home"}))
        candidate = evaluate_candidate(candidate["candidate_id"], decision_fn=lambda _: "prepare_message", policy_config=NO_QUIET_HOURS)
        self.assertEqual(candidate["status"], "prepared")
        self.assertEqual(candidate["decision"], "prepare_message")
        stages = [row["stage"] for row in get_audit(candidate["candidate_id"])]
        self.assertEqual(stages, ["candidate", "policy", "decision", "outbox"])

    def test_idle_candidate_defer_or_prepare(self):
        _, candidate = self.candidate_for(self.event("conversation.idle_elapsed", "evt-idle", {"threshold_minutes": 90}))
        self.assertEqual(candidate["route"], "conversation_followup")
        candidate = evaluate_candidate(candidate["candidate_id"], decision_fn=lambda _: "defer", policy_config=NO_QUIET_HOURS)
        self.assertEqual(candidate["status"], "deferred")
        self.assertEqual(candidate["decision"], "defer")

    def test_duplicate_event_and_candidate_are_idempotent(self):
        event = self.event("location.returned_home", "evt-duplicate", {"from": "outside", "to": "at_home"})
        first = ingest_events([event])
        second = ingest_events([event])
        self.assertTrue(first[0]["inserted"])
        self.assertFalse(second[0]["inserted"])
        candidate_id = f"candidate_{__import__('hashlib').sha256(b'evt-duplicate:welcome_home').hexdigest()[:24]}"
        self.assertIsNotNone(get_candidate(candidate_id))
        self.assertEqual(len([row for row in get_audit(candidate_id) if row["stage"] == "candidate"]), 1)

    def test_candidate_execute_once_and_expiry(self):
        _, candidate = self.candidate_for(self.event("location.returned_home", "evt-exec", {"from": "outside", "to": "at_home"}))
        prepared = evaluate_candidate(candidate["candidate_id"], decision_fn=lambda _: "prepare_message", policy_config=NO_QUIET_HOURS)
        executed = execute_candidate(prepared["candidate_id"])
        self.assertTrue(executed["ok"])
        second = execute_candidate(prepared["candidate_id"])
        self.assertFalse(second["ok"])

        event = {"event_id": "expired-event", "event_type": "location.returned_home"}
        expired = build(event, {}, now=datetime(2026, 1, 1, tzinfo=timezone.utc), ttl_minutes=1)
        result = evaluate(expired, {}, now=datetime(2026, 1, 1, 0, 2, tzinfo=timezone.utc), config=NO_QUIET_HOURS)
        self.assertEqual(result.action, "expired")

    def test_policy_cooldown_quiet_budget_and_duplicate(self):
        candidate = build({"event_id": "e", "event_type": "location.returned_home"}, {}, now=datetime(2026, 8, 10, 10, tzinfo=timezone.utc))
        self.assertFalse(evaluate(candidate, {"same_route_last_sent_minutes": 5}, now=datetime(2026, 8, 10, 10, tzinfo=timezone.utc), config=NO_QUIET_HOURS).allowed)
        self.assertFalse(evaluate(candidate, {"daily_action_count": 3}, now=datetime(2026, 8, 10, 10, tzinfo=timezone.utc), config=NO_QUIET_HOURS).allowed)
        self.assertFalse(evaluate(candidate, {"duplicate_candidate": True}, now=datetime(2026, 8, 10, 10, tzinfo=timezone.utc), config=NO_QUIET_HOURS).allowed)
        self.assertFalse(evaluate(candidate, {}, now=datetime(2026, 8, 10, 23, tzinfo=timezone.utc)).allowed)

    def test_outbox_retry_and_dead_letter(self):
        item = outbox.enqueue({"candidate_id": "retry-candidate", "context_snapshot": {}}, "prepare_message")
        now = datetime.now(timezone.utc)
        for _ in range(outbox.MAX_ATTEMPTS):
            result = outbox.execute_pending(lambda _: (_ for _ in ()).throw(RuntimeError("failure")), now=now)
            self.assertTrue(result)
            item = result[0]
            if item["status"] == "retry":
                item["next_attempt_at"] = now.isoformat()
        self.assertEqual(item["status"], "dead_letter")
        self.assertEqual(item["attempts"], outbox.MAX_ATTEMPTS)


if __name__ == "__main__":
    unittest.main()
