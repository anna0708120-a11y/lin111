"""Phase 10 guarded capability dispatch with audit-ready results."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .mcp_registry import CapabilityRegistry, registry

_last_calls: dict[str, datetime] = {}


def dispatch(name: str, arguments: dict[str, Any], *, capability_registry: CapabilityRegistry = registry) -> dict[str, Any]:
    capability = capability_registry.get(name)
    if capability is None:
        return {"ok": False, "error": "capability_not_found", "capability": name}
    if capability.side_effect:
        return {"ok": False, "error": "side_effect_requires_life_action", "capability": name}
    now = datetime.now(timezone.utc)
    previous = _last_calls.get(name)
    if previous and (now - previous).total_seconds() < capability.cooldown_seconds:
        return {"ok": False, "error": "capability_cooldown", "capability": name}
    if not callable(capability.executor):
        return {"ok": False, "error": "capability_unavailable", "capability": name}
    _last_calls[name] = now
    try:
        result = capability.executor(dict(arguments or {}))
        return {"ok": bool(result.get("ok", True)) if isinstance(result, dict) else True, "capability": name, "result": result}
    except Exception as exc:
        return {"ok": False, "capability": name, "error": str(exc)[:500]}


def reset_dispatch_state() -> None:
    _last_calls.clear()
