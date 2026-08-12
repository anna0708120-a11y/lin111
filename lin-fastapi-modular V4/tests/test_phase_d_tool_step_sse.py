import json
import unittest

from app.agent.event_bus import Timeline


class ToolStepSseTests(unittest.TestCase):
    def test_timeline_emits_tool_step_update(self):
        event = Timeline(trace_id="trace-test").emit(
            id="context_read", type="tool", status="running", summary="Reading context"
        )
        payload = Timeline(trace_id="trace-test").to_sse(event)
        self.assertIn("event: tool_step_update", payload)
        self.assertIn('"status": "running"', payload)


if __name__ == "__main__":
    unittest.main()
