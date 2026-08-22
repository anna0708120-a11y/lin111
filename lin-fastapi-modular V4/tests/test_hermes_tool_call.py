import json

import pytest

from app.integrations.hermes_tool_call import (
    HERMES_AGENT_TOOL,
    build_tool_result_messages,
    run_hermes_tool_call,
    stream_hermes_tool_call,
)


class FakeBridge:
    def __init__(self):
        self.started = []

    def start_run(self, payload):
        self.started.append(payload)
        return {"run_id": "run_1", "status": "accepted"}

    def stream_events(self, run_id):
        assert run_id == "run_1"
        yield {"run_id": run_id, "sequence": 1, "type": "agent.started", "status": "running"}
        yield {"run_id": run_id, "sequence": 2, "type": "tool.started", "status": "running", "tool_name": "web_search", "args_preview": "news"}
        yield {"run_id": run_id, "sequence": 3, "type": "tool.completed", "status": "success", "tool_name": "web_search", "result_preview": "found"}
        yield {"run_id": run_id, "sequence": 4, "type": "agent.completed", "status": "success"}

    def get_run(self, run_id):
        return {"run_id": run_id, "status": "completed", "result": "Hermes final answer"}


class FailingBridge(FakeBridge):
    def stream_events(self, run_id):
        yield {"run_id": run_id, "sequence": 1, "type": "tool.started", "status": "running", "tool_name": "web_search", "tool_id": "tool_a"}
        raise RuntimeError("runtime stream dropped")


def test_hermes_tool_schema_requires_prompt_and_supports_existing_run_fields():
    function = HERMES_AGENT_TOOL["function"]
    assert function["name"] == "run_hermes_agent"
    assert function["parameters"]["required"] == ["prompt"]
    assert set(function["parameters"]["properties"]) == {"prompt", "context", "session_id", "enabled_toolsets", "skills"}


def test_run_hermes_tool_call_preserves_real_lifecycle_and_final_result():
    bridge = FakeBridge()
    events = []
    result = run_hermes_tool_call(
        bridge,
        call_id="call_1",
        arguments=json.dumps({"prompt": "search news", "enabled_toolsets": ["web"]}),
        emit=events.append,
    )

    assert bridge.started == [{"prompt": "search news", "enabled_toolsets": ["web"]}]
    assert [event["type"] for event in events] == ["agent.start", "tool.start", "tool.complete", "agent.complete"]
    assert events[1]["tool_id"] == "run_1:2"
    assert events[2]["tool_id"] == "run_1:2"
    assert result == "Hermes final answer"


def test_stream_hermes_tool_call_marks_started_agent_failed_on_runtime_error():
    events = []
    with pytest.raises(RuntimeError, match="stream dropped"):
        for kind, data in stream_hermes_tool_call(FailingBridge(), call_id="call_1", arguments='{"prompt":"search"}'):
            events.append((kind, data))
    assert [data["type"] for kind, data in events if kind == "agent_event"] == ["agent.start", "tool.start", "agent.failed"]


def test_tool_result_messages_preserve_required_assistant_tool_alternation():
    call = {"id": "call_1", "name": "run_hermes_agent", "arguments": '{"prompt":"search"}'}
    messages = build_tool_result_messages(call, "Hermes final answer", "Before ")
    assert [message["role"] for message in messages] == ["assistant", "tool"]
    assert messages[0]["content"] == "Before "
    assert messages[0]["tool_calls"][0]["id"] == "call_1"
    assert messages[1] == {"role": "tool", "tool_call_id": "call_1", "content": "Hermes final answer"}


def test_run_hermes_tool_call_rejects_incomplete_or_invalid_arguments():
    with pytest.raises(ValueError, match="prompt"):
        run_hermes_tool_call(FakeBridge(), call_id="call_1", arguments='{"prompt":""}', emit=lambda event: None)
