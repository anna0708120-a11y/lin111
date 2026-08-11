"""Phase 6 normalization from existing context and chat payloads."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .contracts import LifeEvent, iso_utc


def _json_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _event(
    event_type: str,
    source: str,
    payload: dict[str, Any],
    *,
    occurred_at: Any = None,
    confidence: float = 1.0,
    session_id: str | None = None,
    dedupe_payload: Any = None,
) -> LifeEvent:
    occurred = iso_utc(occurred_at)
    stable = payload if dedupe_payload is None else dedupe_payload
    dedupe = hashlib.sha256(f"{event_type}|{source}|{_json_key(stable)}".encode()).hexdigest()
    event_id = f"life_{dedupe[:24]}"
    return LifeEvent(
        event_id,
        event_type,
        source,
        occurred,
        iso_utc(datetime.now(timezone.utc)),
        payload,
        max(0.0, min(1.0, float(confidence))),
        dedupe,
        session_id=session_id,
    )


def _payload_time(payload: dict[str, Any]) -> Any:
    return payload.get("timestamp") or payload.get("updated_at") or payload.get("occurred_at") or payload.get("time")


def normalize_location(payload: dict[str, Any], previous_state: str = "unknown") -> list[LifeEvent]:
    """Only classify an explicit Home automation event or label as location state.

    Coordinates and arbitrary place labels do not establish whether Anna is at home;
    upstream must provide an explicit home/away semantic signal.
    """
    if not isinstance(payload, dict):
        return []
    raw_state = str(
        payload.get("state")
        or payload.get("location_state")
        or payload.get("location_event")
        or ""
    ).strip().lower()
    state_map = {
        "arrive_home": "at_home",
        "returned_home": "at_home",
        "home": "at_home",
        "at_home": "at_home",
        "leave_home": "outside",
        "left_home": "outside",
        "outside": "outside",
    }
    state = state_map.get(raw_state)
    if state is None:
        label = str(payload.get("label") or "").strip().lower()
        if label in {"home", "at_home", "家", "家中", "家裡"}:
            state = "at_home"
        # A generic label such as an office, coordinate, or place name is not
        # reliable enough to infer that Anna has left home.
    if state is None or state == previous_state:
        return []
    observed_at = iso_utc(_payload_time(payload))
    transition = {"from": previous_state, "to": state, "observed_at": observed_at}
    kind = "location.returned_home" if state == "at_home" else "location.left_home"
    return [_event(
        kind,
        "location",
        transition,
        occurred_at=observed_at,
        confidence=float(payload.get("confidence", 0.8)),
        dedupe_payload={"from": previous_state, "to": state, "occurred_at": observed_at},
    )]


def normalize_mac(payload: dict[str, Any], previous_state: str = "unknown", previous_charging: bool | None = None) -> list[LifeEvent]:
    if not isinstance(payload, dict):
        return []
    if payload.get("asleep") is True:
        state = "idle"
    elif payload.get("locked") is True:
        state = "locked"
    elif payload.get("asleep") is False or payload.get("locked") is False:
        state = "active"
    else:
        return []
    if state == previous_state:
        return []
    mapping = {
        ("unknown", "active"): "mac.active",
        ("idle", "active"): "mac.active",
        ("locked", "active"): "mac.unlocked",
        ("active", "idle"): "mac.idle",
        ("active", "locked"): "mac.locked",
    }
    event_type = mapping.get((previous_state, state), "mac.state_changed")
    events = [_event(event_type, "mac", {"from": previous_state, "to": state}, occurred_at=_payload_time(payload), confidence=0.95, dedupe_payload={"from": previous_state, "to": state, "occurred_at": iso_utc(_payload_time(payload))})]
    charging = payload.get("charging")
    if isinstance(charging, bool) and charging != previous_charging:
        events.append(_event("mac.charging_changed", "mac", {"charging": charging}, occurred_at=_payload_time(payload), confidence=0.95, dedupe_payload={"charging": charging, "occurred_at": iso_utc(_payload_time(payload))}))
    return events


def normalize_screentime(payload: dict[str, Any], previous_total: int | None = None) -> list[LifeEvent]:
    if not isinstance(payload, dict) or payload.get("total_minutes") is None:
        return []
    total = int(payload.get("total_minutes") or 0)
    date_key = str(payload.get("date") or datetime.now(timezone.utc).date().isoformat())
    if previous_total is not None and total == previous_total:
        return []
    level = "low" if total < 120 else "moderate" if total < 360 else "high"
    body = {"total_minutes": total, "activity": level, "date": date_key}
    return [_event("screentime.summary", "screentime", body, occurred_at=_payload_time(payload), confidence=0.98, dedupe_payload=body)]


def normalize_calendar(events: list[dict[str, Any]] | None, now: datetime | None = None) -> list[LifeEvent]:
    result: list[LifeEvent] = []
    occurred = now or datetime.now(timezone.utc)
    for item in events or []:
        if not isinstance(item, dict) or not item.get("title") or not item.get("start"):
            continue
        payload = {"title": str(item["title"])[:200], "start": str(item["start"]), "end": item.get("end"), "location": item.get("location")}
        result.append(_event("calendar.upcoming", "calendar", payload, occurred_at=occurred, confidence=0.9, dedupe_payload=payload))
    return result



def normalize_phone_observation(payload: dict[str, Any]) -> list[LifeEvent]:
    """Normalize a phone-side observation without claiming it is a live OS fact."""
    if not isinstance(payload, dict):
        return []
    app_name = str(payload.get("app_name") or payload.get("app") or "").strip()
    battery_level = payload.get("battery_level")
    battery_state = str(payload.get("battery_state") or "").strip().lower()
    source_kind = str(payload.get("observation_source") or "shortcut").strip().lower()
    if not app_name and battery_level is None and not battery_state:
        return []

    observed_at = iso_utc(_payload_time(payload))
    confidence = 0.95 if source_kind == "shortcut" else 0.35
    body = {
        "app_name": app_name[:160] or None,
        "battery_level": battery_level,
        "battery_state": battery_state or None,
        "observation_source": source_kind,
        "observed_at": observed_at,
    }
    dedupe_body = {key: value for key, value in body.items() if key != "observed_at"}
    dedupe_body["observed_at"] = observed_at
    return [
        _event(
            "phone.observed",
            "iphone",
            body,
            occurred_at=observed_at,
            confidence=confidence,
            dedupe_payload=dedupe_body,
        )
    ]


def normalize_conversation(role: str, content: str, *, session_id: str | None = None, occurred_at: Any = None) -> list[LifeEvent]:
    role = str(role or "").lower()
    if role not in {"anna", "lin", "user", "assistant"} or not str(content or "").strip():
        return []
    event_type = "conversation.user_message" if role in {"anna", "user"} else "conversation.lin_message"
    occurred = iso_utc(occurred_at)
    payload = {"role": role, "content_preview": str(content)[:240]}
    dedupe_payload = {"role": role, "content": str(content), "occurred_at": occurred, "session_id": session_id}
    return [_event(event_type, "conversation", payload, occurred_at=occurred, session_id=session_id, dedupe_payload=dedupe_payload)]
