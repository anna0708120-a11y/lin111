import json

from app.agent.hermes_stream import stream_with_hermes_agent


class FakeBridge:
    def start_run(self, payload):
        assert payload["prompt"] == "search news"
        return {"run_id": "run_1"}

    def stream_events(self, run_id):
        yield {"run_id": run_id, "sequence": 1, "type": "tool.started", "status": "running", "tool_name": "web_search"}
        yield {"run_id": run_id, "sequence": 2, "type": "tool.completed", "status": "success", "tool_name": "web_search"}
        yield {"run_id": run_id, "sequence": 3, "type": "agent.completed", "status": "success"}

    def get_run(self, run_id):
        return {"result": "fresh result"}


def test_stream_runs_one_real_hermes_round_then_resumes_model_text():
    calls = []

    def stream_factory(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            yield "content", "Before "
            yield "tool_call", {"id": "call_1", "name": "run_hermes_agent", "arguments": json.dumps({"prompt": "search news"})}
            yield "raw_reasoning", "first reason"
            yield "done", {}
        else:
            yield "content", "after."
            yield "raw_reasoning", "second reason"
            yield "done", {}

    events = list(stream_with_hermes_agent(stream_factory, FakeBridge()))

    assert [kind for kind, _ in events] == [
        "content", "agent_event", "agent_event", "agent_event", "agent_event",
        "raw_reasoning", "content", "raw_reasoning", "done",
    ]
    assert "tools" in calls[0]
    assert calls[1]["tools"] is None
    assert [message["role"] for message in calls[1]["tool_result"]] == ["assistant", "tool"]
    assert calls[1]["tool_result"][0]["content"] == "Before "
    assert calls[1]["tool_result"][1]["content"] == "fresh result"



def test_stream_rejects_multiple_model_tool_calls_in_one_round():
    def stream_factory(**kwargs):
        yield "tool_call", {"id": "call_a", "name": "run_hermes_agent", "arguments": '{"prompt":"first"}'}
        yield "tool_call", {"id": "call_b", "name": "run_hermes_agent", "arguments": '{"prompt":"second"}'}

    events = list(stream_with_hermes_agent(stream_factory, FakeBridge()))
    assert events == [("error", "multiple Hermes tool calls are not supported in one model round")]


def test_stream_rejects_unknown_model_tool_without_calling_hermes():
    def stream_factory(**kwargs):
        yield "tool_call", {"id": "call_x", "name": "unknown", "arguments": "{}"}
        yield "done", {}

    events = list(stream_with_hermes_agent(stream_factory, FakeBridge()))
    assert events[0][0] == "error"
    assert "unknown tool" in events[0][1]
