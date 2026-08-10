"""Persistence facade for Phase 6 Life records."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app import db
from .contracts import LifeEvent, LifeState, aware_utc, iso_utc


def save_event(event: LifeEvent) -> tuple[dict[str, Any], bool]:
    return db.insert_life_event(event.as_dict())


def list_events(start: datetime | None = None, end: datetime | None = None, limit: int = 500) -> list[dict[str, Any]]:
    return db.load_life_events(start=iso_utc(start) if start else None, end=iso_utc(end) if end else None, limit=limit)


def load_state(subject_id: str = "anna") -> LifeState:
    row = db.load_latest_life_state(subject_id)
    return LifeState.from_dict(row.get("state") if row else None)


def save_state(state: LifeState, *, subject_id: str = "anna", source_event_id: str | None = None, changed_keys: list[str] | None = None) -> dict[str, Any] | None:
    return db.insert_life_state_snapshot({
        "snapshot_id": f"life_state:{subject_id}:{state.version}:{state.updated_at}",
        "subject_id": subject_id,
        "state": state.as_dict(),
        "changed_keys": changed_keys or [],
        "source_event_id": source_event_id,
        "valid_at": state.updated_at or iso_utc(datetime.utcnow()),
        "version": state.version,
    })
