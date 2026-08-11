"""Runtime orchestration for Phase 6, with no LLM or action side effects."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from app import db
from app.event_bus import event_bus

from .contracts import LifeEvent, LifeState, aware_utc, iso_utc
from .event_normalizer import normalize_calendar, normalize_conversation, normalize_location, normalize_mac, normalize_phone_observation, normalize_screentime
from .read_model import dynamic_life_context, format_dynamic_life_context, format_life_context, format_stable_life_context, stable_life_context
from .interpretations import derive_interpretations
from .state_engine import apply_event, mark_conversation_idle

_MEMORY_EVENTS: list[dict[str, Any]] = []
_MEMORY_STATES: dict[str, dict[str, Any]] = {}


def _save_event(event: LifeEvent) -> tuple[dict[str, Any], bool]:
    if not db.is_connected():
        if not any(item.get("event_id") == event.event_id for item in _MEMORY_EVENTS):
            _MEMORY_EVENTS.append(event.as_dict())
            return event.as_dict(), True
        return event.as_dict(), False
    row, inserted = db.insert_life_event(event.as_dict())
    if inserted:
        return row or event.as_dict(), True
    # Keep the current process observable when persistence is unavailable or rejects a row.
    if not any(item.get("event_id") == event.event_id for item in _MEMORY_EVENTS):
        _MEMORY_EVENTS.append(event.as_dict())
        return event.as_dict(), True
    return row or event.as_dict(), False


def _load_state(subject_id: str) -> LifeState:
    if db.is_connected():
        row = db.load_latest_life_state(subject_id)
        return LifeState.from_dict(row.get("state") if row else None)
    return LifeState.from_dict(_MEMORY_STATES.get(subject_id))


def _save_state(state: LifeState, event: LifeEvent, changed: list[str]) -> dict[str, Any] | None:
    row = {
        "snapshot_id": f"life_state:{state.version}:{event.event_id}",
        "subject_id": "anna",
        "state": state.as_dict(),
        "changed_keys": changed,
        "source_event_id": event.event_id,
        "valid_at": state.updated_at,
        "version": state.version,
    }
    if db.is_connected():
        return db.insert_life_state_snapshot(row)
    _MEMORY_STATES["anna"] = deepcopy(state.as_dict())
    return row


def reset_memory_runtime() -> None:
    _MEMORY_EVENTS.clear()
    _MEMORY_STATES.clear()
    try:
        from .phase7 import reset_memory_runtime as reset_phase7
        reset_phase7()
    except Exception:
        pass


def ingest_events(events: Iterable[LifeEvent]) -> list[dict[str, Any]]:
    """Persist normalized events and apply only newly inserted events."""
    results: list[dict[str, Any]] = []
    for event in sorted(events, key=lambda item: aware_utc(item.occurred_at)):
        row, inserted = _save_event(event)
        state = _load_state(event.subject_id)
        changed: list[str] = []
        snapshot = None
        if inserted:
            next_state, changed = apply_event(state, event)
            if changed:
                snapshot = _save_state(next_state, event, changed)
            event_bus.emit("life", f"Life event: {event.event_type}")
            try:
                from .phase7 import create_candidates_for_events
                create_candidates_for_events([{**event.as_dict(), "state": next_state.as_dict() if changed else state.as_dict()}])
            except Exception as phase7_error:
                print(f"[life] candidate 建立失敗: {phase7_error}")
        results.append({"event": row, "inserted": inserted, "changed_keys": changed, "snapshot": snapshot})
    return results


def ingest_context(source: str, payload: dict[str, Any], *, previous_state: LifeState | None = None) -> list[dict[str, Any]]:
    state = previous_state or _load_state("anna")
    if source == "location":
        events = normalize_location(payload, state.location_state)
    elif source == "mac":
        events = normalize_mac(payload, state.mac_state, state.mac_charging)
    elif source == "screentime":
        previous_total = None
        recent = list_events(limit=20)
        for row in reversed(recent):
            if row.get("event_type") == "screentime.summary":
                previous_total = (row.get("payload") or {}).get("total_minutes")
                break
        events = normalize_screentime(payload, previous_total)
    elif source == "calendar":
        events = normalize_calendar(payload if isinstance(payload, list) else [])
    elif source == "phone":
        events = normalize_phone_observation(payload)
    else:
        events = []
    return ingest_events(events)


def ingest_conversation(role: str, content: str, *, session_id: str | None = None, occurred_at: Any = None) -> list[dict[str, Any]]:
    return ingest_events(normalize_conversation(role, content, session_id=session_id, occurred_at=occurred_at))


def list_events(start: datetime | None = None, end: datetime | None = None, limit: int = 500) -> list[dict[str, Any]]:
    persisted = []
    if db.is_connected():
        persisted = db.load_life_events(start=iso_utc(start) if start else None, end=iso_utc(end) if end else None, limit=limit)
    rows_by_id = {row.get("event_id"): row for row in persisted if row.get("event_id")}
    for row in _MEMORY_EVENTS:
        occurred = aware_utc(row.get("occurred_at"))
        if start and occurred < aware_utc(start):
            continue
        if end and occurred >= aware_utc(end):
            continue
        rows_by_id.setdefault(row.get("event_id"), row)
    rows = list(rows_by_id.values())
    rows.sort(key=lambda row: aware_utc(row.get("occurred_at")))
    return rows[-limit:]


def get_life_state(subject_id: str = "anna") -> dict[str, Any]:
    return _load_state(subject_id).as_dict()


def get_timeline(date_text: str, *, timezone_name: str = "Asia/Hong_Kong") -> list[dict[str, Any]]:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(timezone_name)
    start_local = datetime.fromisoformat(date_text).replace(tzinfo=tz)
    start = start_local.astimezone(timezone.utc)
    end = (start_local + timedelta(days=1)).astimezone(timezone.utc)
    rows = list_events(start=start, end=end, limit=1000)
    labels = {"location.returned_home": "returned home", "location.left_home": "left home", "mac.active": "Mac active", "mac.idle": "Mac idle", "mac.locked": "Mac locked", "mac.unlocked": "Mac unlocked", "conversation.user_message": "user message", "conversation.lin_message": "Lin message", "screentime.summary": "screen time summary", "calendar.upcoming": "calendar upcoming"}
    return [{"event_id": row.get("event_id"), "event_type": row.get("event_type"), "time": aware_utc(row.get("occurred_at")).astimezone(tz).strftime("%H:%M"), "label": labels.get(row.get("event_type"), row.get("event_type")), "payload": row.get("payload") or {}, "confidence": row.get("confidence")} for row in rows]


def get_life_context(*, timezone_name: str = "Asia/Hong_Kong", now: datetime | None = None) -> dict[str, Any]:
    current_time = now or datetime.now(timezone.utc)
    recent = list_events(
        start=aware_utc(current_time) - timedelta(hours=24),
        end=aware_utc(current_time) + timedelta(minutes=1),
        limit=12,
    )
    stable = stable_life_context()
    dynamic = dynamic_life_context(timezone_name=timezone_name, now=current_time, events=recent)
    return {
        "stable": stable,
        "dynamic": dynamic,
        "state": get_life_state(),
        "recent_events": dynamic["recent_events"],
        "interpretations": derive_interpretations(recent, now=aware_utc(current_time)),
        "timezone": timezone_name,
    }


def get_life_context_text(*, timezone_name: str = "Asia/Hong_Kong") -> str:
    context = get_life_context(timezone_name=timezone_name)
    return "\n\n".join([
        format_stable_life_context(context["stable"]),
        format_dynamic_life_context(context["dynamic"]),
    ])


def replay_events(events: Iterable[LifeEvent], *, subject_id: str = "anna") -> LifeState:
    state = LifeState.from_dict(None)
    for event in sorted(events, key=lambda item: aware_utc(item.occurred_at)):
        state, _ = apply_event(state, event)
    return state


def mark_idle(now: datetime | None = None, threshold_minutes: int = 90) -> list[dict[str, Any]]:
    state = _load_state("anna")
    next_state, changed = mark_conversation_idle(state, now or datetime.now(timezone.utc), threshold_minutes)
    if not changed:
        return []
    event = LifeEvent(
        event_id=f"life_idle_{iso_utc(now or datetime.now(timezone.utc))}", event_type="conversation.idle_elapsed", source="conversation", occurred_at=iso_utc(now or datetime.now(timezone.utc)), received_at=iso_utc(datetime.now(timezone.utc)), payload={"threshold_minutes": threshold_minutes}, confidence=1.0, dedupe_key=f"conversation.idle_elapsed:{state.last_user_activity_at}:{threshold_minutes}")
    return ingest_events([event])
