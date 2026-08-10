"""Phase 6 Life System contracts and time helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

UTC = timezone.utc


def aware_utc(value: Any, fallback: datetime | None = None) -> datetime:
    """Normalize an ISO/datetime value to timezone-aware UTC."""
    if isinstance(value, datetime):
        parsed = value
    elif value:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            parsed = fallback or datetime.now(UTC)
    else:
        parsed = fallback or datetime.now(UTC)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def iso_utc(value: Any) -> str:
    return aware_utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class LifeEvent:
    event_id: str
    event_type: str
    source: str
    occurred_at: str
    received_at: str
    payload: dict[str, Any]
    confidence: float
    dedupe_key: str
    subject_id: str = "anna"
    session_id: str | None = None
    schema_version: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "subject_id": self.subject_id,
            "session_id": self.session_id,
            "occurred_at": self.occurred_at,
            "received_at": self.received_at,
            "payload": self.payload,
            "confidence": self.confidence,
            "dedupe_key": self.dedupe_key,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class LifeState:
    location_state: str = "unknown"
    mac_state: str = "unknown"
    mac_charging: bool | None = None
    screen_activity: str = "unknown"
    current_schedule: dict[str, Any] | None = None
    next_schedule: dict[str, Any] | None = None
    conversation_state: str = "unknown"
    ignored_streak: int = 0
    awaiting_reply_since: str | None = None
    last_action_at: str | None = None
    daily_action_count: int = 0
    last_user_activity_at: str | None = None
    last_conversation_at: str | None = None
    updated_at: str | None = None
    version: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "location_state": self.location_state,
            "mac_state": self.mac_state,
            "mac_charging": self.mac_charging,
            "screen_activity": self.screen_activity,
            "current_schedule": self.current_schedule,
            "next_schedule": self.next_schedule,
            "conversation_state": self.conversation_state,
            "ignored_streak": self.ignored_streak,
            "awaiting_reply_since": self.awaiting_reply_since,
            "last_action_at": self.last_action_at,
            "daily_action_count": self.daily_action_count,
            "last_user_activity_at": self.last_user_activity_at,
            "last_conversation_at": self.last_conversation_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "LifeState":
        value = value if isinstance(value, dict) else {}
        return cls(
            location_state=str(value.get("location_state") or "unknown"),
            mac_state=str(value.get("mac_state") or "unknown"),
            mac_charging=value.get("mac_charging") if isinstance(value.get("mac_charging"), bool) else None,
            screen_activity=str(value.get("screen_activity") or "unknown"),
            current_schedule=value.get("current_schedule") if isinstance(value.get("current_schedule"), dict) else None,
            next_schedule=value.get("next_schedule") if isinstance(value.get("next_schedule"), dict) else None,
            conversation_state=str(value.get("conversation_state") or "unknown"),
            ignored_streak=int(value.get("ignored_streak") or 0),
            awaiting_reply_since=value.get("awaiting_reply_since"),
            last_action_at=value.get("last_action_at"),
            daily_action_count=int(value.get("daily_action_count") or 0),
            last_user_activity_at=value.get("last_user_activity_at"),
            last_conversation_at=value.get("last_conversation_at"),
            updated_at=value.get("updated_at"),
            version=int(value.get("version") or 0),
        )
