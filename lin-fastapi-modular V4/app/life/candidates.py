"""Phase 7 candidate lifecycle and deterministic decision boundary."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable

STATUSES = {"pending", "evaluating", "deferred", "dropped", "prepared", "sent", "completed", "failed", "expired"}
DECISIONS = {"no_action", "record_diary", "update_life_state", "prepare_message", "send_message", "defer", "drop"}


def candidate_id(source_event_id: str, route: str) -> str:
    digest = hashlib.sha256(f"{source_event_id}:{route}".encode()).hexdigest()[:24]
    return f"candidate_{digest}"


def build(event: dict[str, Any], state: dict[str, Any], *, now: datetime | None = None, ttl_minutes: int = 180, route: str | None = None) -> dict[str, Any] | None:
    event_type = str(event.get("event_type") or "")
    if event_type == "location.returned_home":
        route = route or "welcome_home"
        seed = "Anna 回到家了"
        priority = 0.7
    elif event_type == "conversation.idle_elapsed":
        route = route or "conversation_followup"
        seed = "Anna 很久沒有回覆"
        priority = 0.45
    else:
        return None
    created = now or datetime.now(timezone.utc)
    expires = created.timestamp() + ttl_minutes * 60
    candidate_key = candidate_id(str(event["event_id"]), route)
    return {
        "candidate_id": candidate_key,
        "source_event_id": event["event_id"],
        "route": route,
        "category": "relationship" if route == "conversation_followup" else "life_transition",
        "created_at": created.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "expires_at": datetime.fromtimestamp(expires, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "priority": priority,
        "score": priority,
        "status": "pending",
        "context_snapshot": {"event": event, "state": state, "message_seed": seed},
        "decision": None,
        "decision_reason": None,
        "action_reference": None,
    }


def is_expired(candidate: dict[str, Any], now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    expires = str(candidate.get("expires_at") or "").replace("Z", "+00:00")
    try:
        return now.astimezone(timezone.utc) >= datetime.fromisoformat(expires).astimezone(timezone.utc)
    except ValueError:
        return True


def normalize_decision(value: str | None) -> str:
    value = str(value or "no_action").strip().lower()
    aliases = {"send": "send_message", "prepare": "prepare_message", "drop": "drop", "defer": "defer", "none": "no_action"}
    return aliases.get(value, value if value in DECISIONS else "no_action")


def decide(candidate: dict[str, Any], *, policy_action: str, policy_reason: str, decision_fn: Callable[[dict[str, Any]], str] | None = None) -> tuple[str, str]:
    if policy_action == "expired":
        return "no_action", "candidate_expired"
    if policy_action in {"defer", "drop"}:
        return policy_action, policy_reason
    proposed = decision_fn(candidate) if decision_fn else ("prepare_message" if candidate.get("route") == "welcome_home" else "defer")
    decision = normalize_decision(proposed)
    return decision, "ai_decision_or_local_fallback"
