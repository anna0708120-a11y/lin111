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


def test_brain_stream_maps_real_agent_events_to_existing_sse_contract():
    assert "stream_with_hermes_agent" in BRAIN
    assert "configured_hermes_bridge" in BRAIN
    assert "event_type == \"agent_event\"" in BRAIN
    assert 'event: agent_event' in BRAIN
