"""Deterministic Life Event -> Life State transitions."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .contracts import LifeEvent, LifeState, iso_utc


def apply_event(state: LifeState, event: LifeEvent) -> tuple[LifeState, list[str]]:
    values = state.as_dict()
    changed: list[str] = []
    p = event.payload
    et = event.event_type
    if et in {"location.observed", "location.changed", "location.returned_home", "location.left_home"}:
        new = p.get("to") if et != "location.observed" else p.get("state")
        if new and new != values["location_state"]:
            values["location_state"] = new; changed.append("location_state")
        observed_at = p.get("observed_at") or event.occurred_at
        if observed_at and observed_at != values.get("location_observed_at"):
            values["location_observed_at"] = observed_at; changed.append("location_observed_at")
    elif et.startswith("mac.") and p.get("to"):
        if p["to"] != values["mac_state"]:
            values["mac_state"] = p["to"]; changed.append("mac_state")
    elif et == "mac.charging_changed":
        if p.get("charging") != values.get("mac_charging"):
            values["mac_charging"] = p.get("charging"); changed.append("mac_charging")
    elif et == "screentime.summary":
        if p.get("activity") != values["screen_activity"]:
            values["screen_activity"] = p.get("activity"); changed.append("screen_activity")
    elif et == "calendar.upcoming":
        current = values.get("next_schedule")
        if current != p:
            values["next_schedule"] = deepcopy(p); changed.append("next_schedule")
    elif et == "calendar.started":
        if values.get("current_schedule") != p:
            values["current_schedule"] = deepcopy(p); changed.append("current_schedule")
        if values.get("next_schedule") == p:
            values["next_schedule"] = None; changed.append("next_schedule")
    elif et == "calendar.ended":
        if values.get("current_schedule") == p:
            values["current_schedule"] = None; changed.append("current_schedule")
    elif et == "conversation.user_message":
        values["conversation_state"] = "active"
        values["last_user_activity_at"] = event.occurred_at
        values["last_conversation_at"] = event.occurred_at
        values["ignored_streak"] = 0
        values["awaiting_reply_since"] = None
        changed.extend(["conversation_state", "last_user_activity_at", "last_conversation_at", "ignored_streak", "awaiting_reply_since"])
    elif et == "conversation.lin_message":
        values["conversation_state"] = "active"
        values["last_conversation_at"] = event.occurred_at
        changed.extend(["conversation_state", "last_conversation_at"])
    elif et == "conversation.idle_elapsed":
        if values.get("conversation_state") != "idle":
            values["conversation_state"] = "idle"; changed.append("conversation_state")
    elif et == "life.action_result":
        if p.get("action"):
            values["last_action_at"] = event.occurred_at; changed.append("last_action_at")
        if p.get("action") == "send_message" and p.get("ok"):
            values["awaiting_reply_since"] = event.occurred_at
            changed.append("awaiting_reply_since")
        if p.get("route") == "conversation_followup" and p.get("action") == "send_message" and p.get("ok"):
            values["ignored_streak"] = int(values.get("ignored_streak") or 0) + 1
            changed.append("ignored_streak")
    if not changed:
        return state, []
    values["updated_at"] = event.occurred_at
    values["version"] = state.version + 1
    return LifeState.from_dict(values), list(dict.fromkeys(changed))


def mark_conversation_idle(state: LifeState, now: datetime, threshold_minutes: int = 90) -> tuple[LifeState, list[str]]:
    if not state.last_user_activity_at:
        return state, []
    elapsed = (now.astimezone(timezone.utc) - datetime.fromisoformat(state.last_user_activity_at.replace("Z", "+00:00"))).total_seconds() / 60
    if elapsed < threshold_minutes or state.conversation_state != "active":
        return state, []
    values = state.as_dict(); values["conversation_state"] = "idle"; values["updated_at"] = iso_utc(now); values["version"] = state.version + 1
    return LifeState.from_dict(values), ["conversation_state"]
