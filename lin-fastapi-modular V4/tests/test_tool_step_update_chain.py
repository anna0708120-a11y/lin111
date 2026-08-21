from pathlib import Path


ROOT = Path(__file__).parents[1]
FRONTEND = (ROOT / "app/web/frontend.py").read_text()
ACTIVITY_JS = (ROOT / "static/js/agent_activity.js").read_text()


def test_watch_parser_accepts_event_bus_tool_step_update_envelope():
    assert "currentEvent === 'tool_step_update'" in FRONTEND
    assert "data.event" in FRONTEND
    assert "handleTimelineEvent(data.event" in FRONTEND


def test_normal_stream_event_names_remain_unchanged():
    assert "currentEvent === 'text_delta'" in FRONTEND
    assert "currentEvent === 'reasoning'" in FRONTEND
    assert "currentEvent === 'tool_step_update'" in FRONTEND


def test_activity_adapter_still_owns_real_tool_lifecycle_events():
    assert "type === 'tool.start'" in ACTIVITY_JS
    assert "type === 'tool.progress'" in ACTIVITY_JS
    assert "type === 'tool.complete'" in ACTIVITY_JS
    assert "handleTimelineEvent" in ACTIVITY_JS
    assert "event.type === 'memory'" in ACTIVITY_JS
