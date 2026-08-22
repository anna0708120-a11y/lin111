import json
from unittest.mock import Mock, patch

from app.llm.openai_compatible import OpenAICompatibleProvider


def _sse(*frames):
    return [b"data: " + json.dumps(frame).encode() for frame in frames] + [b"data: [DONE]"]


def test_stream_accumulates_fragmented_openai_tool_arguments_before_emitting():
    response = Mock()
    response.raise_for_status.return_value = None
    response.iter_lines.return_value = _sse(
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "type": "function", "function": {"name": "run_hermes_agent", "arguments": "{\"prompt\":\"search"}}]}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": " news\"}"}}]}, "finish_reason": "tool_calls"}]},
    )
    provider = OpenAICompatibleProvider(name="gpt", api_key="test", base_url="https://api.example/v1", model="model")
    tools = [{"type": "function", "function": {"name": "run_hermes_agent", "parameters": {"type": "object"}}}]

    with patch("app.llm.openai_compatible.requests.post", return_value=response) as post:
        events = list(provider.stream_chat("system", tools=tools))

    assert events == [
        ("tool_call", {"id": "call_1", "name": "run_hermes_agent", "arguments": '{"prompt":"search news"}'}),
        ("raw_reasoning", ""),
        ("done", {}),
    ]
    assert post.call_args.kwargs["json"]["tools"] == tools
    assert post.call_args.kwargs["json"]["tool_choice"] == "auto"
