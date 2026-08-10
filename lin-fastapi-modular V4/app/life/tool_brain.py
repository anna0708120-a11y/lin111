"""Phase 9 backend Tool Brain: constrained suggestions, never direct actions."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


def suggest_with_backend(candidate: dict[str, Any]) -> dict[str, Any]:
    """Use Groq only when explicitly enabled; otherwise stay deterministic."""
    try:
        from .groq_brain import decide
        result = decide(candidate)
        if result.get("ok"):
            return result
    except Exception as exc:
        return {"ok": False, "decision": "no_tool", "reason": f"backend_error:{str(exc)[:200]}"}
    return suggest(candidate).as_dict()


@dataclass(frozen=True)
class ToolSuggestion:
    decision: str
    reason: str
    tool: str | None = None
    arguments: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "tool": self.tool,
            "arguments": self.arguments or {},
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }


def suggest(candidate: dict[str, Any]) -> ToolSuggestion:
    """Conservative fallback planner until Groq is configured.

    This function deliberately returns suggestions only. The caller must route
    any tool result back through the existing policy/outbox boundary.
    """
    route = str(candidate.get("route") or "")
    if route == "welcome_home":
        return ToolSuggestion("no_tool", "life_event_has_sufficient_local_context")
    if route == "conversation_followup":
        return ToolSuggestion("no_tool", "relationship_context_requires_no_external_lookup")
    return ToolSuggestion("no_tool", "no_safe_tool_needed")


def run_suggestion(candidate: dict[str, Any], executor: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None) -> dict[str, Any]:
    suggestion = suggest(candidate).as_dict()
    return _execute_suggestion(suggestion, executor)


def run_backend_suggestion(candidate: dict[str, Any]) -> dict[str, Any]:
    suggestion = suggest_with_backend(candidate)
    if isinstance(suggestion, ToolSuggestion):
        suggestion = suggestion.as_dict()
    return _execute_suggestion(dict(suggestion), _dispatch_registered_tool)


def _dispatch_registered_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from .tool_executor import dispatch
    return dispatch(tool_name, arguments)


def _execute_suggestion(suggestion: dict[str, Any], executor: Callable[[str, dict[str, Any]], dict[str, Any]] | None) -> dict[str, Any]:
    if suggestion.get("decision") != "search" or not executor:
        return {"suggestion": suggestion, "executed": False, "result": None}
    query = str(suggestion.get("query") or suggestion.get("arguments", {}).get("query") or "")[:500]
    if not query:
        return {"suggestion": {**suggestion, "decision": "no_tool", "reason": "empty_search_query"}, "executed": False, "result": None}
    result = executor("web.search", {"query": query})
    return {"suggestion": {**suggestion, "tool": "web.search", "arguments": {"query": query}}, "executed": True, "result": result}
