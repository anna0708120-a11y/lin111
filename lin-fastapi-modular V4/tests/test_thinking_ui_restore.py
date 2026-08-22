from pathlib import Path

ROOT = Path(__file__).parents[1]
CHAT_VIEW = (ROOT / "static/js/chat_view.js").read_text()
ACTIVITY = (ROOT / "static/js/agent_activity.js").read_text()
FRONTEND = (ROOT / "app/web/frontend.py").read_text()


def test_history_restores_existing_thinking_toggle_and_box():
    assert 'think-toggle' in CHAT_VIEW
    assert 'think-box' in CHAT_VIEW
    assert 'toggleThink(this)' in CHAT_VIEW
    assert 'message.think' in CHAT_VIEW


def test_live_thinking_is_an_independent_message_level_region():
    assert "closest('.msg')" in ACTIVITY
    assert "lin-agent-thinking" in ACTIVITY
    assert "insertBefore(box" in ACTIVITY


def test_thinking_and_agent_activity_remain_separate_paths():
    assert "if (type === 'thinking.delta'" in ACTIVITY
    assert "event.type === 'memory'" in ACTIVITY
    assert "currentEvent === 'reasoning'" in FRONTEND
    assert "currentEvent === 'tool_step_update'" in FRONTEND
