"""Phase 7 audit records and lifecycle transitions."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app import db


def record(*, candidate_id: str, stage: str, status: str, reason: str = "", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    row = {
        "audit_id": f"audit:{candidate_id}:{stage}:{datetime.now(timezone.utc).timestamp()}",
        "candidate_id": candidate_id,
        "stage": stage,
        "status": status,
        "reason": reason,
        "payload": payload or {},
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    return db.insert_life_audit(row)


def list_records(candidate_id: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    return db.load_life_audits(candidate_id=candidate_id, limit=limit)
