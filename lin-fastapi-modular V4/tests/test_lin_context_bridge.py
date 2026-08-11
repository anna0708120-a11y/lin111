import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException

from app.integration.lin_context import build_lin_context, verify_lin_context_token


class LinContextBridgeTests(unittest.TestCase):
    @patch("app.integration.lin_context.get_life_context")
    @patch("app.integration.lin_context.state")
    def test_context_is_first_person_and_contains_only_read_projections(self, state, get_life_context):
        state.current_session_id = "session-1"
        state.get_recent_conversation.return_value = [
            {"role": "anna", "content": "我今天完成了重要的事", "time": "2026-08-11T10:00:00"},
            {"role": "lin", "content": "我記得", "time": "2026-08-11T10:01:00", "thinking": "private"},
        ]
        state.relevant_memory_candidates.return_value = [
            {"id": 7, "category": "共同記憶", "tag": "重要", "content": "Anna完成了一件重要的事", "importance": 5}
        ]
        state.get_main_model.return_value = {
            "provider": "deepseek", "model": "deepseek-v4-flash",
            "capabilities": {"reasoning": True},
        }
        get_life_context.return_value = {
            "stable": {"location_state": "home", "current_schedule": None},
            "dynamic": {"recent_events": [{"event_type": "conversation.user_message", "payload": {"text": "private"}}]},
            "state": {"version": 12, "ignored_streak": 99},
            "recent_events": [],
            "timezone": "Asia/Hong_Kong",
        }

        result = build_lin_context(task_type="general", memory_query="重要的事")

        self.assertEqual(result["schema_version"], "lin-context/v1")
        self.assertTrue(result["identity"]["first_person"])
        self.assertIn("Lin", result["identity"]["persona"])
        self.assertEqual(result["continuity"]["session_id"], "session-1")
        self.assertEqual(result["memory"]["relevant"][0]["content"], "Anna完成了一件重要的事")
        self.assertNotIn("thinking", result["continuity"]["recent_conversation"][1])
        self.assertNotIn("ignored_streak", result["life"]["context"]["state"])
        self.assertNotIn("text", result["life"]["context"]["recent_events"][0].get("payload", {}))
        self.assertNotIn("api_key", str(result).lower())
        self.assertLess(
            datetime.fromisoformat(result["expires_at"].replace("Z", "+00:00")),
            datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=16),
        )

    def test_bridge_token_is_fail_closed(self):
        with patch.dict(os.environ, {"LIN_CONTEXT_API_TOKEN": "bridge-secret"}, clear=False):
            with patch("app.integration.lin_context.config.LIN_CONTEXT_API_TOKEN", "bridge-secret"):
                self.assertTrue(verify_lin_context_token("Bearer bridge-secret"))
                with self.assertRaises(HTTPException) as missing:
                    verify_lin_context_token("")
                self.assertEqual(missing.exception.status_code, 401)
                with self.assertRaises(HTTPException) as bad:
                    verify_lin_context_token("Bearer wrong")
                self.assertEqual(bad.exception.status_code, 401)

    def test_bridge_token_is_unavailable_when_unconfigured(self):
        with patch("app.integration.lin_context.config.LIN_CONTEXT_API_TOKEN", ""):
            with self.assertRaises(HTTPException) as exc:
                verify_lin_context_token("Bearer anything")
            self.assertEqual(exc.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
