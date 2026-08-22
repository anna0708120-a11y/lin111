"""Small adapter that runs one model-requested Hermes Agent task."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from app.integrations.hermes_bridge import HermesBridge


HERMES_AGENT_TOOL = {
    "type": "function",
    "function": {
        "name": "run_hermes_agent",
        "description": "Run a task through Lin's configured Hermes Agent runtime and return its final answer.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "prompt": {"type": "string", "minLength": 1},
                "context": {"type": "string"},
                "session_id": {"type": "string"},
                "enabled_toolsets": {"type": "array", "items": {"type": "string"}},
                "skills": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["prompt"],
        },
    },
}


def _event_type(event: dict[str, Any]) -> str:
    return str(event.get("type") or "").lower()


def build_tool_result_messages(call: dict[str, Any], result: str, assistant_content: str | None = None) -> list[dict[str, Any]]:
    """Build the assistant/tool pair required by OpenAI-compatible follow-up calls."""
    return [
        {
            "role": "assistant",
            "content": assistant_content,
            "tool_calls": [{
                "id": call["id"],
                "type": "function",
                "function": {"name": call["name"], "arguments": call["arguments"]},
            }],
        },
        {"role": "tool", "tool_call_id": call["id"], "content": result},
    ]


def stream_hermes_tool_call(
    bridge: HermesBridge,
    *,
    call_id: str,
    arguments: str,
):
    try:
        payload = json.loads(arguments)
    except (TypeError, ValueError) as exc:
        raise ValueError("run_hermes_agent arguments must be valid JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("prompt"), str) or not payload["prompt"].strip():
        raise ValueError("run_hermes_agent requires a non-empty prompt")

    accepted = bridge.start_run(payload)
    run_id = str(accepted.get("run_id") or "")
    if not run_id:
        raise ValueError("Hermes Runtime did not return run_id")
    yield "agent_event", {"type": "agent.start", "id": run_id, "summary": "Hermes Agent", "status": "running"}

    active_tools: dict[str, str] = {}
    try:
        for event in bridge.stream_events(run_id):
            event_type = _event_type(event)
            tool_name = str(event.get("tool_name") or event.get("entity") or "Hermes Agent")
            if event_type == "tool.started":
                tool_id = str(event.get("tool_id") or f"{run_id}:{event.get('sequence', 'tool')}")
                active_tools[tool_name] = tool_id
            else:
                tool_id = active_tools.get(tool_name) or str(event.get("tool_id") or f"{run_id}:{event.get('sequence', 'tool')}")
            common = {
                "id": tool_id, "tool_id": tool_id, "name": tool_name,
                "summary": event.get("args_preview") or event.get("result_preview") or event.get("error"),
                "status": event.get("status"), "run_id": run_id, "sequence": event.get("sequence"),
            }
            if event_type == "tool.started":
                yield "agent_event", {"type": "tool.start", **common}
            elif event_type == "tool.completed":
                yield "agent_event", {"type": "tool.complete", **common, "is_error": event.get("status") in {"failed", "error"} or bool(event.get("error"))}
            elif event_type == "tool.progress":
                yield "agent_event", {"type": "tool.progress", **common}
            elif event_type == "agent.completed":
                yield "agent_event", {"type": "agent.complete", "id": run_id, "summary": "Hermes Agent", "status": "success"}
            elif event_type == "agent.failed":
                yield "agent_event", {"type": "agent.failed", "id": run_id, "summary": event.get("error") or "Hermes Agent failed", "status": "failed", "is_error": True}

        final = bridge.get_run(run_id)
        result = final.get("result") if isinstance(final, dict) else None
        if not isinstance(result, str) or not result.strip():
            raise ValueError("Hermes Runtime completed without a final result")
        yield "tool_result", result
    except Exception as exc:
        yield "agent_event", {"type": "agent.failed", "id": run_id, "summary": str(exc), "status": "failed", "is_error": True}
        raise


def run_hermes_tool_call(
    bridge: HermesBridge,
    *,
    call_id: str,
    arguments: str,
    emit: Callable[[dict[str, Any]], None],
) -> str:
    result = None
    for kind, data in stream_hermes_tool_call(bridge, call_id=call_id, arguments=arguments):
        if kind == "agent_event":
            emit(data)
        elif kind == "tool_result":
            result = data
    if result is None:
        raise ValueError("Hermes Runtime completed without a final result")
    return result
