"""Read-only Render -> Hermes context projection for Lin."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Header, HTTPException

from app import config
from app.life.runtime import get_life_context
from app.persona import PERSONA_CORE
from app.state import state
from app.style import STYLE_GUIDE


def verify_lin_context_token(authorization: str = Header(default="")) -> bool:
    """Fail closed: the bridge is unavailable unless explicitly configured."""
    token = config.LIN_CONTEXT_API_TOKEN
    if not token:
        raise HTTPException(status_code=503, detail="LIN_CONTEXT_API_TOKEN not configured")
    expected = f"Bearer {token}"
    if not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="unauthorized")
    return True


def _version(*parts: Any) -> str:
    payload = "\n".join(repr(part) for part in parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _conversation_projection(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    result = []
    for row in rows[-limit:]:
        role = row.get("role")
        if role not in {"anna", "lin", "user", "assistant"}:
            continue
        result.append({
            "role": "anna" if role in {"anna", "user"} else "lin",
            "content": str(row.get("content") or ""),
            "time": row.get("time"),
        })
    return result


def _memory_projection(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    fields = ("id", "category", "tag", "content", "importance", "keyword")
    return [{key: row.get(key) for key in fields} for row in rows[:limit]]


def _life_projection(raw: dict[str, Any]) -> dict[str, Any]:
    stable = raw.get("stable") or {}
    dynamic = raw.get("dynamic") or {}
    source_state = raw.get("state") or {}
    state = {
        key: source_state.get(key)
        for key in ("location_state", "location_observed_at", "mac_state", "screen_activity",
                    "current_schedule", "next_schedule", "conversation_state", "updated_at", "version")
        if key in source_state
    }
    recent = []
    for event in (dynamic.get("recent_events") or raw.get("recent_events") or [])[: config.LIN_CONTEXT_LIFE_EVENT_LIMIT]:
        recent.append({
            key: event.get(key)
            for key in ("event_type", "occurred_at", "confidence")
            if key in event
        } | {"payload": {k: v for k, v in (event.get("payload") or {}).items() if k in {"label", "source", "summary"}}})
    return {
        "timezone": raw.get("timezone"),
        "stable": {key: stable.get(key) for key in (
            "location_state", "location_observed_at", "mac_state", "screen_activity",
            "conversation_state", "current_schedule", "next_schedule") if key in stable},
        "state": state,
        "recent_events": recent,
    }


def build_lin_context(*, task_type: str = "general", session_id: str | None = None,
                      memory_query: str = "") -> dict[str, Any]:
    """Build an allowlisted, non-mutating snapshot of the current Lin state."""
    current_session = session_id or state.current_session_id
    conversations = _conversation_projection(
        state.get_recent_conversation(n=config.LIN_CONTEXT_CONVERSATION_LIMIT),
        config.LIN_CONTEXT_CONVERSATION_LIMIT,
    )
    query = memory_query or (conversations[-1]["content"] if conversations else "")
    memories = _memory_projection(
        state.relevant_memory_candidates(query, n=config.LIN_CONTEXT_MEMORY_LIMIT) if query else [],
        config.LIN_CONTEXT_MEMORY_LIMIT,
    )
    life = _life_projection(get_life_context())
    now = datetime.now(timezone.utc).replace(microsecond=0)
    expires = now + timedelta(seconds=config.LIN_CONTEXT_TTL_SECONDS)
    model = state.get_main_model()
    persona_version = _version(PERSONA_CORE, STYLE_GUIDE)
    memory_revision = _version(memories)
    life_version = life["state"].get("version", 0)
    context_id = secrets.token_urlsafe(18)
    return {
        "schema_version": "lin-context/v1",
        "context_id": context_id,
        "issued_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "task": {"type": task_type, "read_only": True},
        "identity": {
            "subject": "Lin",
            "first_person": True,
            "persona": PERSONA_CORE,
            "style": STYLE_GUIDE,
            "persona_version": persona_version,
        },
        "continuity": {"session_id": current_session, "recent_conversation": conversations},
        "memory": {"revision": memory_revision, "relevant": memories},
        "life": {"state_version": life_version, "context": life},
        "model": {
            "provider": model.get("provider"),
            "model": model.get("model"),
            "capabilities": model.get("capabilities", {}),
        },
    }
