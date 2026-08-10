"""Durable idempotent outbox with bounded exponential retry."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app import db

MAX_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 30
MAX_BACKOFF_SECONDS = 3600
_MEMORY_OUTBOX: dict[str, dict[str, Any]] = {}


def _save(item: dict[str, Any]) -> dict[str, Any]:
    existing = _MEMORY_OUTBOX.get(item["outbox_id"])
    if existing:
        return existing
    _MEMORY_OUTBOX[item["outbox_id"]] = dict(item)
    return _MEMORY_OUTBOX[item["outbox_id"]]


def _update(outbox_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    item = _MEMORY_OUTBOX.setdefault(outbox_id, {"outbox_id": outbox_id})
    item.update(patch)
    return item


def reset_memory_outbox() -> None:
    _MEMORY_OUTBOX.clear()


def enqueue(candidate: dict[str, Any], action: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    row = {
        "outbox_id": f"outbox:{candidate['candidate_id']}:{action}",
        "candidate_id": candidate["candidate_id"],
        "action": action,
        "idempotency_key": f"{candidate['candidate_id']}:{action}",
        "payload": payload or candidate.get("context_snapshot") or {},
        "status": "pending",
        "attempts": 0,
        "next_attempt_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "last_error": None,
    }
    if db.is_connected():
        return db.upsert_life_outbox(row)
    return _save(row)


def _pending_memory(now: datetime, limit: int) -> list[dict[str, Any]]:
    rows = []
    for item in _MEMORY_OUTBOX.values():
        if item.get("status") not in {"pending", "retry"}:
            continue
        next_at = item.get("next_attempt_at")
        try:
            due = datetime.fromisoformat(str(next_at).replace("Z", "+00:00")) if next_at else now
        except ValueError:
            due = now
        if due <= now:
            rows.append(item)
    rows.sort(key=lambda item: str(item.get("next_attempt_at") or ""))
    return rows[:limit]


def execute_pending(sender: Callable[[dict[str, Any]], Any], *, now: datetime | None = None, limit: int = 20) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    items = db.load_pending_life_outbox(now.isoformat(), limit=limit) if db.is_connected() else _pending_memory(now, limit)
    results = []
    for item in items:
        if item.get("status") in {"completed", "dead_letter"}:
            continue
        attempts = int(item.get("attempts") or 0)
        try:
            result = sender(item)
            patch = {"status": "completed", "attempts": attempts + 1, "result": result, "completed_at": now.isoformat()}
        except Exception as exc:
            attempts += 1
            if attempts >= MAX_ATTEMPTS:
                status = "dead_letter"
                next_at = None
            else:
                status = "retry"
                delay = min(MAX_BACKOFF_SECONDS, BASE_BACKOFF_SECONDS * (2 ** max(0, attempts - 1)))
                next_at = (now + timedelta(seconds=delay)).isoformat()
            patch = {"status": status, "attempts": attempts, "last_error": str(exc)[:500], "next_attempt_at": next_at}
        updated = db.update_life_outbox(item["outbox_id"], patch) if db.is_connected() else _update(item["outbox_id"], patch)
        results.append(updated or item)
    return results
