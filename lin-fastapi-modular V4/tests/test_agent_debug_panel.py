from pathlib import Path

ROOT = Path(__file__).parents[1]
FRONTEND = (ROOT / "app/web/frontend.py").read_text()
DEBUG_JS = ROOT / "static/js/agent_debug.js"
DEBUG_CSS = ROOT / "static/agent_debug.css"


def test_debug_panel_is_loaded_and_mounted_below_model_selector():
    assert '/static/js/agent_debug.js' in FRONTEND
    assert '/static/agent_debug.css' in FRONTEND
    assert 'id="agent-debug-panel"' in FRONTEND
    mine = FRONTEND[FRONTEND.index('id="pg-mine"'):]
    assert mine.index('id="agent-debug-panel"') > mine.index('id="main-model-select"')


def test_debug_module_has_core_agent_raw_and_error_sections():
    source = DEBUG_JS.read_text()
    for label in ('Core Pipeline', 'Agent / Tool Pipeline', 'Raw Events', 'Errors'):
        assert label in source
    for key in ('api_start', 'prompt', 'reasoning', 'memory_decision', 'parser', 'backend', 'database'):
        assert key in source
    for key in ('tool_calling', 'backend_emitted', 'sse_received', 'sse_parsed', 'tool_step_update', 'agent_ingest', 'hermes_tool', 'tool_progress', 'tool_complete', 'agent_ui_rendered'):
        assert key in source


def test_debug_preserves_unknown_raw_sse_and_tristate_statuses():
    source = DEBUG_JS.read_text()
    assert 'unknown' in source
    assert 'rawEvents' in source
    assert 'value ===' in source
    assert '—' in source
    assert '✕' in source


def test_debug_uses_real_sse_and_does_not_create_playback_events():
    source = DEBUG_JS.read_text()
    assert 'recordSse' in source
    assert 'tool_step_update' in source
    assert 'setTimeout' not in source
    assert 'playBtn' not in source
