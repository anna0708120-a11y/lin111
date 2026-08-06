"""Read-only serialization for the current Body State UI/SSE payload."""
from datetime import datetime


def _remaining_text(seconds):
    seconds = max(0, int(seconds or 0))
    if seconds <= 0:
        return "已結束"
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"剩 {hours}h {minutes}m"
    return f"剩 {minutes}m"


def build_intimacy_status_payload(state, now=None):
    """Build one backend-owned payload for HTTP status and SSE updates."""
    now = now or datetime.now()
    from app.intimacy.body_state import get_body_description, get_body_level
    from app.intimacy.cycle import get_current_cycle, get_cycle_progress
    from app.intimacy.engine import compute_willingness, get_atmosphere
    from app.intimacy.event import get_event

    cycle = get_current_cycle(state)
    body_values = getattr(state, "body_values", {})
    body_meta = {}
    for key in ("tension", "heat", "sensitivity", "control"):
        value = float(body_values.get(key, 0))
        body_meta[key] = {
            "value": round(value, 1),
            "level": get_body_level(value),
            "desc": get_body_description(key, value),
        }

    cycle_started_at = getattr(state, "cycle_started_at", None)
    cycle_expires_at = getattr(state, "cycle_expires_at", None)
    elapsed_seconds = max(0, int((now - cycle_started_at).total_seconds())) if cycle_started_at else 0
    remaining_seconds = max(0, int((cycle_expires_at - now).total_seconds())) if cycle_expires_at else 0

    active_event = None
    event_key = getattr(state, "active_event_key", None)
    event = get_event(event_key) if event_key else None
    if event:
        expires_at = getattr(state, "active_event_expires_at", None)
        event_remaining_seconds = max(0, int((expires_at - now).total_seconds())) if expires_at else 0
        active_event = {
            "key": event.key,
            "label": event.label,
            "description": event.prompt,
            "started_at": getattr(state, "active_event_started_at", None).isoformat() if getattr(state, "active_event_started_at", None) else None,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "remaining_seconds": event_remaining_seconds,
            "remaining_text": _remaining_text(event_remaining_seconds),
        }

    after_effects = []
    for effect in getattr(state, "active_after_effects", []) or []:
        remaining = max(0, int((effect.expires_at - now).total_seconds()))
        if remaining <= 0:
            continue
        after_effects.append({
            "source_event": effect.source_event,
            "description": effect.description,
            "started_at": effect.started_at.isoformat(),
            "expires_at": effect.expires_at.isoformat(),
            "remaining_seconds": remaining,
            "remaining_text": _remaining_text(remaining),
        })

    mood = getattr(state, "mood", {}) or {}
    willingness = compute_willingness(mood)
    return {
        "willingness": willingness,
        "atmosphere": get_atmosphere(willingness, mood),
        "cycle": {
            "key": cycle.key,
            "label": cycle.label,
            "description": cycle.description,
            "started_at": cycle_started_at.isoformat() if cycle_started_at else None,
            "expires_at": cycle_expires_at.isoformat() if cycle_expires_at else None,
            "progress": round(get_cycle_progress(state, now), 4),
            "elapsed_seconds": elapsed_seconds,
            "remaining_seconds": remaining_seconds,
            "remaining_text": _remaining_text(remaining_seconds),
        },
        "active_event": active_event,
        "after_effects": after_effects,
        "body_values": body_meta,
        "auto_change_desc": (
            f"{cycle.label}基線：\n"
            f"tension(蓄積感) → {cycle.targets['tension']:.0f} ({cycle.growth_rates['tension']:+.1f}/h)\n"
            f"heat(熱度) → {cycle.targets['heat']:.0f} ({cycle.growth_rates['heat']:+.1f}/h)\n"
            f"sensitivity(敏感度) → {cycle.targets['sensitivity']:.0f} ({cycle.growth_rates['sensitivity']:+.1f}/h)\n"
            f"control(控制力) → {cycle.targets['control']:.0f} ({cycle.growth_rates['control']:+.1f}/h)"
        ),
        "updated_at": getattr(state, "last_tick_at", None).isoformat() if getattr(state, "last_tick_at", None) else None,
    }
