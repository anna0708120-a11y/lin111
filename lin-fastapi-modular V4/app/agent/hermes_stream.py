"""One bounded main-model → Hermes Agent → main-model streaming round."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from app.integrations.hermes_bridge import HermesBridge, HermesRuntimeConfig
from app.integrations.hermes_tool_call import (
    HERMES_AGENT_TOOL,
    build_tool_result_messages,
    stream_hermes_tool_call,
)


_ALLOWED_TOOLS = {"run_hermes_agent"}


def configured_hermes_bridge():
    config = HermesRuntimeConfig.from_env()
    if not config.base_url or not config.token:
        return None
    return HermesBridge(config)


def stream_with_hermes_agent(stream_factory: Callable[..., Iterator[tuple[str, Any]]], bridge: Any):
    """Yield provider events while allowing at most one Hermes tool round."""
    first_call = None
    assistant_content: list[str] = []
    deferred: list[tuple[str, Any]] = []
    for kind, data in stream_factory(tools=[HERMES_AGENT_TOOL], tool_choice="auto", tool_result=None):
        if kind == "tool_call":
            if data.get("name") not in _ALLOWED_TOOLS:
                yield "error", f"unknown tool: {data.get('name')}"
                return
            if first_call is not None:
                yield "error", "multiple Hermes tool calls are not supported in one model round"
                return
            first_call = data
            continue
        if first_call is not None:
            if kind != "done":
                deferred.append((kind, data))
            continue
        if kind == "content":
            assistant_content.append(str(data))
        yield kind, data

    if first_call is None:
        return

    result: str | None = None
    try:
        for kind, data in stream_hermes_tool_call(
            bridge,
            call_id=first_call["id"],
            arguments=first_call["arguments"],
        ):
            if kind == "agent_event":
                yield kind, data
            elif kind == "tool_result" and isinstance(data, str):
                result = data
    except Exception as exc:
        yield "error", str(exc)
        return
    if result is None:
        yield "error", "Hermes Runtime completed without a final result"
        return
    yield from deferred

    tool_result = build_tool_result_messages(first_call, result, "".join(assistant_content) or None)
    for kind, data in stream_factory(tools=None, tool_choice=None, tool_result=tool_result):
        yield kind, data
