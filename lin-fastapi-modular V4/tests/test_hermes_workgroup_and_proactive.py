import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.integration.phase_b import receive_hermes_event, reset_callback_runtime
from app.life.candidates import build
from app.web import routes


class HermesWorkgroupAndProactiveTests(unittest.TestCase):
    def setUp(self):
        reset_callback_runtime()

    def event(self, kind, payload, event_id="event-1"):
        return {
            "schema_version": "lin-event/v1", "event_id": event_id,
            "task_id": "task-1", "context_id": "context-1", "type": kind,
            "source": "hermes", "observed_at": "2026-08-12T10:00:00Z",
            "payload": payload,
            "source_versions": {"persona_version": "p1", "memory_revision": "m1", "life_state_version": 1},
        }

    def test_workgroup_message_is_render_persisted_and_allowlisted(self):
        with patch("app.integration.phase_b.db.insert_workgroup_message", return_value={"message_id": "x"}) as insert:
            result = receive_hermes_event(self.event("workgroup.message", {
                "member": "gemma", "text": "evidence preprocessing", "metadata": {"model": "gemma4:31b"},
            }))
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["member"], "gemma")
        insert.assert_called_once()

    def test_workgroup_rejects_unknown_member(self):
        with self.assertRaises(HTTPException) as exc:
            receive_hermes_event(self.event("workgroup.message", {"member": "other", "text": "x"}))
        self.assertEqual(exc.exception.status_code, 422)

    def test_proactive_insufficient_evidence_is_rejected(self):
        with self.assertRaises(HTTPException) as exc:
            receive_hermes_event(self.event("proactive.proposed", {
                "interpretation": {"evidence_sufficient": False}, "message": "hello", "signal_id": "s1",
            }))
        self.assertEqual(exc.exception.status_code, 422)

    @patch("app.integration.phase_b.evaluate_candidate")
    @patch("app.integration.phase_b.create_candidates_for_events")
    @patch("app.integration.phase_b.state.add_log")
    def test_proactive_enters_policy_lifecycle_without_delivery(self, log, create, evaluate):
        create.return_value = [{"candidate_id": "candidate-proactive"}]
        evaluate.return_value = {"candidate_id": "candidate-proactive", "status": "prepared"}
        result = receive_hermes_event(self.event("proactive.proposed", {
            "signal_id": "signal-1", "message": "我想问问你项目进度如何。", "route": "life_followup",
            "interpretation": {"observation": "two observations", "interpretation": "可能在处理项目", "evidence_sufficient": True, "evidence": [{"event_id": "a"}, {"event_id": "b"}], "confidence": 0.6, "expires_at": "2099-01-01T00:00:00Z"},
        }))
        self.assertEqual(result["status"], "prepared")
        create.assert_called_once()
        evaluate.assert_called_once()
        self.assertEqual(result["delivery"], "render_policy_required")

    def test_invalid_workgroup_payload_can_be_retried_with_same_event_id(self):
        event = self.event("workgroup.message", {"member": "unknown", "text": "x"})
        with self.assertRaises(HTTPException):
            receive_hermes_event(event)
        event["payload"]["member"] = "anna"
        with patch("app.integration.phase_b.db.insert_workgroup_message", return_value={"message_id": "retryable"}):
            result = receive_hermes_event(event)
        self.assertEqual(result["status"], "accepted")

    def test_proactive_candidate_does_not_outlive_interpretation_expiry(self):
        candidate = build({"event_id": "event-expiry", "event_type": "proactive.proposed", "payload": {"message": "x", "interpretation": {"expires_at": "2026-08-12T10:01:00Z"}}}, {}, now=__import__("datetime").datetime(2026, 8, 12, 10, 0, tzinfo=__import__("datetime").timezone.utc))
        self.assertEqual(candidate["expires_at"], "2026-08-12T10:01:00Z")

    def test_workgroup_post_rejects_whitespace_only_text(self):
        with self.assertRaises(HTTPException) as exc:
            routes.post_workgroup_message(routes.WorkgroupInput(text="   "))
        self.assertEqual(exc.exception.status_code, 422)

    def test_workgroup_post_writes_new_table(self):
        with patch("app.web.routes.db.insert_workgroup_message", return_value={"message_id": "m1"}) as insert:
            result = routes.post_workgroup_message(routes.WorkgroupInput(text="hello"))
        self.assertEqual(result["status"], "accepted")
        insert.assert_called_once()
        self.assertEqual(insert.call_args.args[1:4], ("anna", "user", "hello"))

    def test_workgroup_feed_reads_new_table(self):
        records = [{"message_id": "m1", "member": "gemma", "content": "x", "metadata": {}, "created_at": "2026-08-12T10:00:00Z"}]
        with patch("app.web.routes.db.load_workgroup_messages", return_value=records):
            result = routes.workgroup_messages_endpoint()
        self.assertEqual(len(result["messages"]), 1)
        self.assertEqual(result["messages"][0]["member"], "gemma")


if __name__ == "__main__":
    unittest.main()
