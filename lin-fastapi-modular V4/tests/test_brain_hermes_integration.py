from pathlib import Path

from app.agent.hermes_stream import configured_hermes_bridge

ROOT = Path(__file__).parents[1]
BRAIN = (ROOT / "app/agent/brain.py").read_text()


def test_hermes_tool_is_disabled_when_runtime_credentials_are_incomplete(monkeypatch):
    monkeypatch.delenv("HERMES_RUNTIME_URL", raising=False)
    monkeypatch.delenv("HERMES_RUNTIME_TOKEN", raising=False)
    assert configured_hermes_bridge() is None

    monkeypatch.setenv("HERMES_RUNTIME_URL", "https://runtime.example")
    assert configured_hermes_bridge() is None


def test_hermes_tool_is_enabled_only_with_complete_runtime_credentials(monkeypatch):
    monkeypatch.setenv("HERMES_RUNTIME_URL", "https://runtime.example")
    monkeypatch.setenv("HERMES_RUNTIME_TOKEN", "token")
    bridge = configured_hermes_bridge()
    assert bridge is not None
    assert bridge.config.base_url == "https://runtime.example"


def test_brain_forwards_hermes_tool_kwargs_to_the_main_model_stream():
    assert "def model_stream(*, tools=None, tool_choice=None, tool_result=None):" in BRAIN
    assert "tools=tools," in BRAIN
    assert "tool_choice=tool_choice," in BRAIN
    assert "tool_result=tool_result," in BRAIN


def test_brain_stream_maps_real_agent_events_to_existing_sse_contract():
    assert "stream_with_hermes_agent" in BRAIN
    assert "configured_hermes_bridge" in BRAIN
    assert "event_type == \"agent_event\"" in BRAIN
    assert 'event: agent_event' in BRAIN
