"""Controlled Phase B Hermes -> Render proposal boundary."""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any

from fastapi import Header, HTTPException

from app import config, db
from app.life.runtime import ingest_events
from app.state import state

ALLOWED_EVENT_TYPES = {"task.completed", "task.failed", "memory.proposed", "life.event.proposed"}
_seen_event_ids: set[str] = set()


def verify_hermes_callback_token(authorization: str = Header(default="")) -> bool:
    token = config.HERMES_CALLBACK_API_TOKEN or config.LIN_CONTEXT_API_TOKEN
    if not token:
        raise HTTPException(status_code=503, detail="HERMES_CALLBACK_API_TOKEN not configured")
    if not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="unauthorized")
    return True


def _required(event: dict[str, Any], key: str) -> Any:
    value = event.get(key)
    if value in (None, ""):
        raise HTTPException(status_code=422, detail=f"missing_{key}")
    return value


def _validate(event: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(event, dict) or event.get("schema_version") != "lin-event/v1":
        raise HTTPException(status_code=422, detail="invalid_schema_version")
    event_type = _required(event, "type")
    if event_type not in ALLOWED_EVENT_TYPES:
        raise HTTPException(status_code=422, detail="event_type_not_allowed")
    for key in ("event_id", "task_id", "context_id", "source", "observed_at", "payload", "source_versions"):
        _required(event, key)
    if event["source"] != "hermes" or not isinstance(event["payload"], dict) or not isinstance(event["source_versions"], dict):
        raise HTTPException(status_code=422, detail="invalid_event_shape")
    for key in ("persona_version", "memory_revision", "life_state_version"):
        _required(event["source_versions"], key)
    try:
        datetime.fromisoformat(str(event["observed_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid_observed_at") from exc
    return event


def _memory_decision(payload: dict[str, Any]) -> dict[str, Any]:
    required = ("action", "importance", "category", "tag", "keyword", "summary")
    if any(payload.get(key) in (None, "") for key in required):
        raise HTTPException(status_code=422, detail="invalid_memory_proposal")
    action = str(payload["action"]).lower()
    if action not in {"create", "reinforce", "update", "conflict", "archive", "none"}:
        raise HTTPException(status_code=422, detail="invalid_memory_action")
    try:
        importance = max(1, min(5, int(payload["importance"])))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="invalid_memory_importance") from exc
    decision = {key: payload[key] for key in required}
    decision["importance"] = importance
    decision["memory_id"] = payload.get("memory_id")
    return decision


def receive_hermes_event(event: dict[str, Any]) -> dict[str, Any]:
    event = _validate(event)
    event_id = str(event["event_id"])
    if event_id in _seen_event_ids:
        return {"status": "duplicate", "event_id": event_id}
    _seen_event_ids.add(event_id)
    event_type = event["type"]
    payload = event["payload"]

    if event_type == "memory.proposed":
        decision = _memory_decision(payload)
        result = state.apply_memory_decision(decision)
        state.add_log("hermes.memory.proposed", f"{event_id}: {result.get('action_taken', 'processed')}")
        return {"status": "accepted", "event_id": event_id, "type": event_type, "decision": decision, "result": result}

    if event_type == "life.event.proposed":
        # Proposal only: no LifeEvent construction or persistence occurs here.
        state.add_log("hermes.life.event.proposed", event_id)
        return {"status": "proposal_received", "event_id": event_id, "type": event_type}

    state.add_log(f"hermes.{event_type}", event_id)
    return {"status": "accepted", "event_id": event_id, "type": event_type}


def reset_callback_runtime() -> None:
    _seen_event_ids.clear()
