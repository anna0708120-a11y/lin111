"""Read models for Life Timeline and safe Main LLM context."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .contracts import LifeState, aware_utc
from .store import list_events, load_state


def timeline_for_date(date_text: str, *, subject_id: str = "anna", timezone_name: str = "Asia/Hong_Kong") -> list[dict[str, Any]]:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(timezone_name)
    start_local = datetime.fromisoformat(date_text).replace(tzinfo=tz)
    rows = list_events(start=start_local.astimezone(timezone.utc), end=(start_local + timedelta(days=1)).astimezone(timezone.utc), limit=1000)
    result = []
    for row in rows:
        occurred = aware_utc(row.get("occurred_at")).astimezone(tz)
        payload = row.get("payload") or {}
        et = row.get("event_type") or "event"
        labels = {
            "location.returned_home": "returned home", "location.left_home": "left home", "location.changed": "location changed",
            "mac.active": "Mac active", "mac.idle": "Mac idle", "mac.locked": "Mac locked", "mac.unlocked": "Mac unlocked",
            "calendar.upcoming": "calendar upcoming", "conversation.user_message": "user message", "conversation.lin_message": "Lin message",
            "screentime.summary": "screen time summary",
        }
        result.append({"event_id": row.get("event_id"), "event_type": et, "time": occurred.strftime("%H:%M"), "label": labels.get(et, et), "payload": payload, "confidence": row.get("confidence")})
    return result


def life_context(*, subject_id: str = "anna", recent_limit: int = 12, timezone_name: str = "Asia/Hong_Kong") -> dict[str, Any]:
    state = load_state(subject_id)
    now = datetime.now(timezone.utc)
    recent = list_events(start=now - timedelta(hours=24), end=now + timedelta(minutes=1), limit=recent_limit)
    return {"state": state.as_dict(), "recent_events": [{"event_type": x.get("event_type"), "occurred_at": x.get("occurred_at"), "payload": x.get("payload") or {}} for x in recent], "timezone": timezone_name}


def format_life_context(context: dict[str, Any]) -> str:
    state = context.get("state") or {}
    lines = ["【Lin Life Context】", f"location={state.get('location_state', 'unknown')}", f"mac={state.get('mac_state', 'unknown')}", f"screen_activity={state.get('screen_activity', 'unknown')}", f"conversation={state.get('conversation_state', 'unknown')}", f"current_schedule={state.get('current_schedule') or 'none'}", f"next_schedule={state.get('next_schedule') or 'none'}"]
    if state.get("last_user_activity_at"): lines.append(f"last_user_activity_at={state['last_user_activity_at']}")
    if state.get("last_conversation_at"): lines.append(f"last_conversation_at={state['last_conversation_at']}")
    lines.append("recent_life_events:")
    for item in context.get("recent_events", [])[:12]:
        lines.append(f"- {item.get('occurred_at')} {item.get('event_type')} {item.get('payload') or {}}")
    return "\n".join(lines)
