from pathlib import Path


ROOT = Path(__file__).parents[1]
FRONTEND = (ROOT / "app/web/frontend.py").read_text()
ACTIVITY = (ROOT / "static/js/agent_activity.js").read_text()


def test_phase3_uses_real_stream_events_without_prototype_playback():
    assert "currentEvent === 'text_delta'" in FRONTEND
    assert "currentEvent === 'reasoning'" in FRONTEND
    assert "currentEvent === 'tool_step_update'" in FRONTEND
    assert "handleTimelineEvent(data.event" in FRONTEND
    assert "setTimeout" not in ACTIVITY
    assert "playBtn" not in ACTIVITY


def test_phase3_keeps_text_segments_and_independent_activity_history():
    assert "this.currentText = null" in ACTIVITY
    assert "createTextSegment()" in ACTIVITY
    assert "this.history = []" in ACTIVITY
    assert "this.history.push(this.activity.snapshot())" in ACTIVITY
    assert "this.activity?.byTool?.has(id)" in ACTIVITY


def test_phase3_restores_history_details_and_filters_memory():
    assert "event.type === 'memory'" in ACTIVITY
    assert "a.events = (item.events || []).map" in ACTIVITY
    assert "a._renderPhase(e)" in ACTIVITY
    assert "classList.toggle('expanded')" in ACTIVITY
