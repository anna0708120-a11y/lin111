"""Action validation and execution boundary for Phase 7."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from .candidates import DECISIONS, normalize_decision

SEND_ENABLED = False


def validate_decision(decision: str | None, *, send_enabled: bool = SEND_ENABLED) -> tuple[str, str]:
    normalized = normalize_decision(decision)
    if normalized == "send_message" and not send_enabled:
        return "prepare_message", "send_message_feature_flag_disabled"
    if normalized not in DECISIONS:
        return "no_action", "unknown_decision"
    return normalized, "decision_accepted"


def execute(action: str, candidate: dict[str, Any], *, send_enabled: bool = SEND_ENABLED, sender: Callable[[dict[str, Any]], Any] | None = None) -> dict[str, Any]:
    action, validation_reason = validate_decision(action, send_enabled=send_enabled)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    if action == "send_message" and sender is not None:
        result = sender(candidate)
        return {"ok": True, "action": action, "result": result, "timestamp": now, "validation_reason": validation_reason}
    if action == "prepare_message":
        return {"ok": True, "action": action, "prepared": True, "message": candidate.get("context_snapshot", {}).get("message_seed", ""), "timestamp": now, "validation_reason": validation_reason}
    if action in {"record_diary", "update_life_state", "no_action"}:
        return {"ok": True, "action": action, "timestamp": now, "validation_reason": validation_reason}
    return {"ok": False, "action": action, "error": "unsupported_action", "timestamp": now, "validation_reason": validation_reason}
