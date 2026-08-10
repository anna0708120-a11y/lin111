"""Phase 7 orchestration: event -> candidate -> policy -> decision -> action."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from app import db

from . import audit, outbox
from .actions import execute
from .candidates import build, decide
from .policy import PolicyConfig, evaluate
from .runtime import ingest_events, list_events, mark_idle

_MEMORY_CANDIDATES: dict[str, dict[str, Any]] = {}
_MEMORY_AUDIT: list[dict[str, Any]] = []


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _candidate_row(candidate: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    if db.is_connected():
        existing = db.load_life_candidate(candidate["candidate_id"])
        if existing:
            return existing, False
        row, ok = db.upsert_life_candidate(candidate)
        return row, ok
    existing = _MEMORY_CANDIDATES.get(candidate["candidate_id"])
    if existing:
        return existing, False
    _MEMORY_CANDIDATES[candidate["candidate_id"]] = dict(candidate)
    return candidate, True


def _update_candidate(candidate_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    patch = dict(patch)
    patch["updated_at"] = _now().isoformat(timespec="seconds").replace("+00:00", "Z")
    if db.is_connected():
        return db.update_life_candidate(candidate_id, patch) or patch
    candidate = _MEMORY_CANDIDATES.setdefault(candidate_id, {"candidate_id": candidate_id})
    candidate.update(patch)
    return candidate


def _audit(candidate_id: str, stage: str, status: str, reason: str = "", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    row = {
        "audit_id": f"audit:{candidate_id}:{stage}:{len(_MEMORY_AUDIT)}",
        "candidate_id": candidate_id,
        "stage": stage,
        "status": status,
        "reason": reason,
        "payload": payload or {},
        "created_at": _now().isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    if db.is_connected():
        return audit.record(candidate_id=candidate_id, stage=stage, status=status, reason=reason, payload=payload)
    _MEMORY_AUDIT.append(row)
    return row


def _context_for(candidate: dict[str, Any], now: datetime) -> dict[str, Any]:
    route = candidate.get("route")
    rows = list_events(limit=500)
    candidates = list(_MEMORY_CANDIDATES.values()) if not db.is_connected() else db.list_life_candidates(limit=500)
    same_route = [row for row in candidates if row.get("route") == route and row.get("status") in {"sent", "completed", "prepared"}]
    last_sent_minutes = None
    if same_route:
        latest = max(str(row.get("updated_at") or row.get("created_at")) for row in same_route)
        try:
            last_sent_minutes = (now - datetime.fromisoformat(latest.replace("Z", "+00:00"))).total_seconds() / 60
        except ValueError:
            pass
    user_events = [row for row in rows if row.get("event_type") == "conversation.user_message"]
    duplicate = any(row.get("source_event_id") == candidate.get("source_event_id") and row.get("route") == route and row.get("candidate_id") != candidate.get("candidate_id") for row in candidates)
    return {
        "duplicate_candidate": duplicate,
        "same_route_last_sent_minutes": last_sent_minutes,
        "last_interaction_minutes": None,
        "daily_action_count": sum(1 for row in candidates if row.get("status") in {"sent", "completed"} and str(row.get("created_at", ""))[:10] == now.date().isoformat()),
        "ignored_streak": int((candidate.get("context_snapshot") or {}).get("state", {}).get("ignored_streak") or 0),
        "awaiting_reply_since": (candidate.get("context_snapshot") or {}).get("state", {}).get("awaiting_reply_since"),
        "awaiting_reply_minutes": 0,
        "recent_user_event_count": len(user_events),
    }


def get_candidate(candidate_id: str) -> dict[str, Any] | None:
    return db.load_life_candidate(candidate_id) if db.is_connected() else _MEMORY_CANDIDATES.get(candidate_id)


def create_candidates_for_events(events: Iterable[dict[str, Any]], *, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or _now()
    created: list[dict[str, Any]] = []
    for event in events:
        candidate = build(event, event.get("state") or {}, now=now)
        if not candidate:
            continue
        row, inserted = _candidate_row(candidate)
        if inserted:
            _audit(candidate["candidate_id"], "candidate", "created", "candidate_created", {"source_event_id": event.get("event_id"), "route": candidate.get("route")})
            created.append(row)
    return created


def ingest_and_build(events: Iterable[Any]) -> dict[str, Any]:
    ingest_result = ingest_events(events)
    candidates: list[dict[str, Any]] = []
    for result in ingest_result:
        event = result.get("event") or {}
        if result.get("inserted"):
            event = dict(event)
            event["state"] = result.get("snapshot", {}).get("state", {}) if isinstance(result.get("snapshot"), dict) else {}
            candidates.extend(create_candidates_for_events([event]))
    return {"events": ingest_result, "candidates": candidates}


def evaluate_candidate(candidate_id: str, *, decision_fn: Callable[[dict[str, Any]], str] | None = None, policy_config: PolicyConfig | None = None, now: datetime | None = None) -> dict[str, Any]:
    candidate = db.load_life_candidate(candidate_id) if db.is_connected() else _MEMORY_CANDIDATES.get(candidate_id)
    if not candidate:
        raise KeyError(candidate_id)
    now = now or _now()
    _update_candidate(candidate_id, {"status": "evaluating"})
    context = _context_for(candidate, now)
    policy = evaluate(candidate, context, now=now, config=policy_config)
    _audit(candidate_id, "policy", "passed" if policy.allowed else policy.action, policy.reason, context)
    if not policy.allowed:
        status = "expired" if policy.action == "expired" else "deferred" if policy.action == "defer" else "dropped"
        return _update_candidate(candidate_id, {"status": status, "decision": policy.action, "decision_reason": policy.reason})
    decision, reason = decide(candidate, policy_action="evaluate", policy_reason=policy.reason, decision_fn=decision_fn)
    from .actions import validate_decision
    action, action_reason = validate_decision(decision)
    status = "prepared" if action == "prepare_message" else "deferred" if action == "defer" else "dropped" if action in {"drop", "no_action"} else "pending"
    updated = _update_candidate(candidate_id, {"status": status, "decision": action, "decision_reason": f"{reason}; {action_reason}"})
    _audit(candidate_id, "decision", action, f"{reason}; {action_reason}", {"decision": action})
    if action == "prepare_message":
        queued = outbox.enqueue(updated, action)
        _audit(candidate_id, "outbox", "queued", "prepare_message_queued", queued)
        updated = _update_candidate(candidate_id, {"action_reference": queued.get("outbox_id")})
    return updated


def execute_candidate(candidate_id: str, *, sender: Callable[[dict[str, Any]], Any] | None = None, send_enabled: bool = False) -> dict[str, Any]:
    candidate = _MEMORY_CANDIDATES.get(candidate_id) if not db.is_connected() else db.load_life_candidate(candidate_id)
    if not candidate:
        raise KeyError(candidate_id)
    if candidate.get("status") in {"completed", "sent", "expired", "dropped", "failed"}:
        return {"ok": False, "status": candidate.get("status"), "reason": "candidate_not_executable"}
    if candidate.get("expires_at") and __import__("app.life.candidates", fromlist=["is_expired"]).is_expired(candidate):
        updated = _update_candidate(candidate_id, {"status": "expired", "decision_reason": "candidate_expired"})
        _audit(candidate_id, "action", "expired", "candidate_expired")
        return {"ok": False, "status": "expired", "reason": "candidate_expired", "candidate": updated}
    action = candidate.get("decision") or "no_action"
    result = execute(action, candidate, sender=sender, send_enabled=send_enabled)
    status = "sent" if result.get("ok") and result.get("action") == "send_message" else "completed" if result.get("ok") else "failed"
    updated = _update_candidate(candidate_id, {"status": status})
    _audit(candidate_id, "action", status, result.get("validation_reason") or result.get("error", ""), result)
    from .contracts import LifeEvent, iso_utc
    now = _now()
    event = LifeEvent(
        event_id=f"life_action:{candidate_id}:{status}",
        event_type="life.action_result",
        source="life_runtime",
        occurred_at=iso_utc(now),
        received_at=iso_utc(now),
        payload={"candidate_id": candidate_id, "action": action, "route": candidate.get("route"), "ok": bool(result.get("ok")), "status": status},
        confidence=1.0,
        dedupe_key=f"life.action_result:{candidate_id}:{status}",
    )
    from .runtime import ingest_events
    ingest_events([event])
    return {**result, "candidate": updated}


def reset_memory_runtime() -> None:
    """Reset only the Phase 7 process-local fallback used by tests."""
    _MEMORY_CANDIDATES.clear()
    _MEMORY_AUDIT.clear()


def run_life_runtime_tick(*, now: datetime | None = None, policy_config: PolicyConfig | None = None) -> dict[str, Any]:
    """Background reconciliation with no direct message delivery."""
    now = now or _now()
    idle_events = mark_idle(now=now)
    candidates = list(_MEMORY_CANDIDATES.values()) if not db.is_connected() else db.list_life_candidates(limit=500)
    evaluated = []
    for candidate in candidates:
        if candidate.get("status") not in {"pending", "deferred"}:
            continue
        try:
            evaluated.append(evaluate_candidate(candidate["candidate_id"], policy_config=policy_config, now=now))
        except Exception as exc:
            _audit(candidate.get("candidate_id", "unknown"), "tick", "failed", str(exc)[:300])
    return {"idle_events": idle_events, "evaluated_candidates": evaluated}


def drain_outbox(*, now: datetime | None = None) -> list[dict[str, Any]]:
    """Execute only previously approved non-send actions from the persistent outbox."""
    now = now or _now()

    def execute_item(item: dict[str, Any]) -> dict[str, Any]:
        candidate = _MEMORY_CANDIDATES.get(item["candidate_id"]) if not db.is_connected() else db.load_life_candidate(item["candidate_id"])
        if not candidate:
            raise RuntimeError("candidate_missing")
        result = execute(item.get("action"), candidate, send_enabled=False)
        if not result.get("ok"):
            raise RuntimeError(str(result.get("error") or "action_failed"))
        _update_candidate(candidate["candidate_id"], {"status": "completed"})
        _audit(candidate["candidate_id"], "outbox", "completed", result.get("validation_reason", ""), result)
        return result

    return outbox.execute_pending(execute_item, now=now)


def get_audit(candidate_id: str | None = None) -> list[dict[str, Any]]:
    if db.is_connected():
        return audit.list_records(candidate_id=candidate_id)
    return [row for row in _MEMORY_AUDIT if candidate_id is None or row.get("candidate_id") == candidate_id]
