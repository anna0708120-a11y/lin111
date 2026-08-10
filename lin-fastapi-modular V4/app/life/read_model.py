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


def dynamic_life_context(
    *,
    subject_id: str = "anna",
    now: datetime | None = None,
    recent_limit: int = 12,
    phone_ttl_minutes: int = 25,
    timezone_name: str = "Asia/Hong_Kong",
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build per-turn facts that are intentionally kept out of stable prompt context."""
    now = aware_utc(now or datetime.now(timezone.utc))
    recent = events if events is not None else list_events(
        start=now - timedelta(hours=24),
        end=now + timedelta(minutes=1),
        limit=recent_limit,
    )
    phone = None
    for row in reversed(recent):
        if row.get("event_type") != "phone.observed":
            continue
        observed_at = aware_utc(row.get("occurred_at"))
        age_minutes = max(0, int((now - observed_at).total_seconds() // 60))
        if age_minutes > phone_ttl_minutes:
            continue
        payload = row.get("payload") or {}
        source = str(payload.get("observation_source") or "unknown")
        confidence = float(row.get("confidence") or 0)
        phone = {
            "app_name": payload.get("app_name"),
            "battery_level": payload.get("battery_level"),
            "battery_state": payload.get("battery_state"),
            "source": source,
            "confidence": confidence,
            "observed_at": row.get("occurred_at"),
            "age_minutes": age_minutes,
            "fresh": True,
            "current_claim_allowed": source == "shortcut" and confidence >= 0.9,
            "usable_for_proactive_action": source == "shortcut" and confidence >= 0.9,
        }
        break
    return {
        "generated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "timezone": timezone_name,
        "phone": phone,
        "recent_events": [
            {
                "event_type": row.get("event_type"),
                "occurred_at": row.get("occurred_at"),
                "payload": row.get("payload") or {},
                "confidence": row.get("confidence"),
            }
            for row in recent
        ],
    }


def stable_life_context(*, subject_id: str = "anna") -> dict[str, Any]:
    """Return only replayed LifeState facts suitable for a cacheable prompt prefix."""
    state = load_state(subject_id).as_dict()
    return {
        "subject_id": subject_id,
        "location_state": state.get("location_state", "unknown"),
        "mac_state": state.get("mac_state", "unknown"),
        "screen_activity": state.get("screen_activity", "unknown"),
        "conversation_state": state.get("conversation_state", "unknown"),
        "current_schedule": state.get("current_schedule"),
        "next_schedule": state.get("next_schedule"),
    }


def format_stable_life_context(context: dict[str, Any]) -> str:
    return "\n".join([
        "【Lin Stable Life Context】",
        f"location={context.get('location_state', 'unknown')}",
        f"mac={context.get('mac_state', 'unknown')}",
        f"screen_activity={context.get('screen_activity', 'unknown')}",
        f"conversation={context.get('conversation_state', 'unknown')}",
        f"current_schedule={context.get('current_schedule') or 'none'}",
        f"next_schedule={context.get('next_schedule') or 'none'}",
    ])


def format_dynamic_life_context(context: dict[str, Any]) -> str:
    lines = ["【Lin Dynamic Life Context】"]
    phone = context.get("phone")
    if phone:
        parts = []
        if phone.get("app_name"):
            parts.append(f"recent_phone_app={phone['app_name']}")
        if phone.get("battery_level") is not None:
            parts.append(f"phone_battery={phone['battery_level']}%")
        if phone.get("battery_state"):
            parts.append(f"phone_battery_state={phone['battery_state']}")
        parts.extend([
            f"source={phone.get('source')}",
            f"age_minutes={phone.get('age_minutes')}",
            f"confidence={phone.get('confidence')}",
        ])
        lines.append("phone_observation=" + ", ".join(parts))
    return "\n".join(lines)


def format_life_context(context: dict[str, Any]) -> str:
    """Legacy prompt renderer; callers should migrate to explicit stable/dynamic sections."""
    state = context.get("state") or context
    lines = [
        "【Lin Life Context】",
        f"location={state.get('location_state', 'unknown')}",
        f"mac={state.get('mac_state', 'unknown')}",
        f"screen_activity={state.get('screen_activity', 'unknown')}",
        f"conversation={state.get('conversation_state', 'unknown')}",
        f"current_schedule={state.get('current_schedule') or 'none'}",
        f"next_schedule={state.get('next_schedule') or 'none'}",
    ]
    return "\n".join(lines)
