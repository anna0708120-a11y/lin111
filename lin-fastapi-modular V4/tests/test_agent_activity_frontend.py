from pathlib import Path


ROOT = Path(__file__).parents[1]
FRONTEND = (ROOT / "app/web/frontend.py").read_text()
ACTIVITY_JS = ROOT / "static/js/agent_activity.js"
ACTIVITY_CSS = ROOT / "static/agent_activity.css"
CHAT_VIEW = (ROOT / "static/js/chat_view.js").read_text()


def test_single_chat_loads_the_dedicated_agent_activity_module():
    assert '/static/agent_activity.css' in FRONTEND
    assert '/static/js/agent_activity.js' in FRONTEND
    assert ACTIVITY_JS.exists()
    assert ACTIVITY_CSS.exists()


def test_activity_module_preserves_text_segments_and_tool_history():
    source = ACTIVITY_JS.read_text()
    assert 'createTextSegment' in source
    assert 'new Activity(this.container)' in source
    assert 'this.history = []' in source
    assert "this.currentText = null" in source
    assert "activity.complete" in source
    assert "classList.toggle('expanded')" in source


def test_only_real_agent_or_tool_events_create_activity_nodes():
    source = ACTIVITY_JS.read_text()
    assert "type.startsWith('tool.')" in source
    assert "type.startsWith('agent.')" in source
    assert "api_start" not in source
    assert "Response Streaming" not in source


def test_chat_history_uses_the_agent_activity_history_mount_point():
    assert 'window.AgentActivity' in CHAT_VIEW
    assert 'mountHistory(slot, trace)' in CHAT_VIEW


def test_legacy_tool_card_is_not_loaded_into_the_single_chat_surface():
    assert '/static/js/dev_panel.js' not in FRONTEND
    assert '.tool-card{' not in FRONTEND
