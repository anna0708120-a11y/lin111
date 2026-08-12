"""Controlled Phase B Hermes -> Render proposal boundary."""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any

from fastapi import Header, HTTPException

from app import config, db
from app.life.phase7 import create_candidates_for_events, evaluate_candidate
from app.state import state

ALLOWED_EVENT_TYPES = {"task.completed", "task.failed", "memory.proposed", "life.event.proposed", "workgroup.message", "proactive.proposed"}
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
    event_type = event["type"]
    payload = event["payload"]

    if event_type == "workgroup.message":
        member = str(payload.get("member") or "").lower()
        text = str(payload.get("text") or "").strip()
        metadata = payload.get("metadata") or {}
        if member not in {"anna", "lin", "gemma"} or not text or not isinstance(metadata, dict):
            raise HTTPException(status_code=422, detail="invalid_workgroup_message")
        stored = db.insert_workgroup_message(str(event["event_id"]), member, "assistant", text[:4000], metadata)
        if not stored:
            raise HTTPException(status_code=503, detail="workgroup_storage_unavailable")
        _seen_event_ids.add(event_id)
        return {"status": "accepted", "event_id": event_id, "type": event_type, "member": member}

    if event_type == "proactive.proposed":
        interpretation = payload.get("interpretation") or {}
        message = str(payload.get("message") or "").strip()
        signal_id = str(payload.get("signal_id") or "").strip()
        if not signal_id or not message or not isinstance(interpretation, dict) or not interpretation.get("evidence_sufficient"):
            raise HTTPException(status_code=422, detail="insufficient_proactive_evidence")
        evidence = interpretation.get("evidence") or []
        if len(evidence) < 2 or not interpretation.get("expires_at"):
            raise HTTPException(status_code=422, detail="invalid_proactive_evidence")
        proposal = dict(event)
        proposal["event_type"] = "proactive.proposed"
        candidates = create_candidates_for_events([proposal])
        if not candidates:
            raise HTTPException(status_code=422, detail="invalid_proactive_proposal")
        candidate = candidates[0]
        evaluated = evaluate_candidate(candidate["candidate_id"], decision_fn=lambda _: "prepare_message")
        state.add_log("hermes.proactive.proposed", signal_id)
        _seen_event_ids.add(event_id)
        return {
            "status": evaluated.get("status"), "event_id": event_id,
            "signal_id": signal_id, "candidate_id": evaluated["candidate_id"],
            "delivery": "render_policy_required",
        }

    if event_type == "memory.proposed":
        decision = _memory_decision(payload)
        result = state.apply_memory_decision(decision)
        state.add_log("hermes.memory.proposed", f"{event_id}: {result.get('action_taken', 'processed')}")
        _seen_event_ids.add(event_id)
        return {"status": "accepted", "event_id": event_id, "type": event_type, "decision": decision, "result": result}

    if event_type == "life.event.proposed":
        # Proposal only: no LifeEvent construction or persistence occurs here.
        state.add_log("hermes.life.event.proposed", event_id)
        _seen_event_ids.add(event_id)
        return {"status": "proposal_received", "event_id": event_id, "type": event_type}

    _seen_event_ids.add(event_id)
    state.add_log(f"hermes.{event_type}", event_id)
    return {"status": "accepted", "event_id": event_id, "type": event_type}


def reset_callback_runtime() -> None:
    _seen_event_ids.clear()
