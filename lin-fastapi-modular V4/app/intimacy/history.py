"""Small helpers for recording inspectable Body State snapshots in event metadata."""


def build_body_state_snapshot(state):
    """Return JSON-safe current state for event and settlement audit records."""
    def iso(value):
        return value.isoformat() if value else None

    effects = []
    for effect in getattr(state, "active_after_effects", []) or []:
        effects.append({
            "source_event": effect.source_event,
            "description": effect.description,
            "expires_at": iso(effect.expires_at),
        })

    return {
        "body_values": {
            key: round(float(getattr(state, "body_values", {}).get(key, 0)), 1)
            for key in ("tension", "heat", "sensitivity", "control")
        },
        "cycle_key": getattr(state, "cycle_key", "stable"),
        "active_event_key": getattr(state, "active_event_key", None),
        "last_tick_at": iso(getattr(state, "last_tick_at", None)),
        "after_effects": effects,
    }
