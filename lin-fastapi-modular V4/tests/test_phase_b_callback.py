import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.integration.phase_b import receive_hermes_event, reset_callback_runtime


class PhaseBCallbackTests(unittest.TestCase):
    def setUp(self):
        reset_callback_runtime()

    def event(self, event_type="task.completed", payload=None):
        return {
            "schema_version": "lin-event/v1",
            "event_id": "event-1",
            "task_id": "task-1",
            "context_id": "context-1",
            "type": event_type,
            "source": "hermes",
            "observed_at": "2026-08-11T10:00:00Z",
            "payload": payload or {"summary": "done"},
            "source_versions": {
                "persona_version": "p1",
                "memory_revision": "m1",
                "life_state_version": 1,
            },
        }

    def test_accepts_task_result_without_arbitrary_database_write(self):
        with patch("app.integration.phase_b.db.save_state_value") as save, patch("app.integration.phase_b.state.add_log") as log:
            result = receive_hermes_event(self.event())
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["type"], "task.completed")
        log.assert_called_once()
        save.assert_not_called()

    def test_rejects_unlisted_event_type(self):
        with self.assertRaises(HTTPException) as exc:
            receive_hermes_event(self.event("memory.created"))
        self.assertEqual(exc.exception.status_code, 422)

    @patch("app.integration.phase_b.state.apply_memory_decision")
    def test_memory_proposal_is_sent_through_render_lifecycle(self, apply):
        apply.return_value = {"success": True, "memory_id": 42, "action_taken": "created"}
        result = receive_hermes_event(self.event("memory.proposed", {
            "action": "create", "importance": 5, "category": "长期记忆",
            "tag": "重要", "keyword": "important_fact", "summary": "Anna told me an important fact.",
        }))
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["decision"]["summary"], "Anna told me an important fact.")
        apply.assert_called_once()

    @patch("app.integration.phase_b.create_candidates_for_events")
    def test_life_proposal_is_not_written_without_render_approval(self, create_candidates):
        result = receive_hermes_event(self.event("life.event.proposed", {
            "event_type": "mac.active", "payload": {"to": "active"}
        }))
        self.assertEqual(result["status"], "proposal_received")
        create_candidates.assert_not_called()

    def test_duplicate_event_is_idempotent(self):
        with patch("app.integration.phase_b.state.add_log") as log:
            first = receive_hermes_event(self.event("task.failed", {"error": "x"}))
            second = receive_hermes_event(self.event("task.failed", {"error": "x"}))
        self.assertEqual(first["status"], "accepted")
        self.assertEqual(second["status"], "duplicate")
        self.assertEqual(log.call_count, 1)


if __name__ == "__main__":
    unittest.main()
