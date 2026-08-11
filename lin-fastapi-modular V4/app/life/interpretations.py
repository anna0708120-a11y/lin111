"""Bounded, read-only interpretations derived from recent Life evidence."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from app import db

_ENABLED_KINDS = {"workload.focus"}
_WORK_TERMS = {
    "work", "project", "computer", "task", "busy", "schedule", "workload",
    "工作", "项目", "專案", "项目", "电脑", "電腦", "任务", "任務", "忙", "行程", "日程", "排程",
}


def _utc(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_evidence(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event.get("event_id"),
        "event_type": event.get("event_type"),
        "occurred_at": event.get("occurred_at"),
        "confidence": event.get("confidence"),
    }


def _workload_focus(events: list[dict[str, Any]], now: datetime) -> dict[str, Any] | None:
    recent = []
    for event in events:
        occurred = _utc(event.get("occurred_at"))
        if not occurred or now - occurred > timedelta(hours=4) or occurred > now:
            continue
        if float(event.get("confidence") or 0) < 0.8:
            continue
        if event.get("event_type") in {"mac.active", "mac.unlocked", "screentime.summary", "calendar.upcoming"}:
            recent.append(event)

    mac_events = [event for event in recent if event.get("event_type") in {"mac.active", "mac.unlocked"}]
    supporting_events = [event for event in recent if event.get("event_type") in {"screentime.summary", "calendar.upcoming"}]
    if len(mac_events) < 2 or not supporting_events:
        return None

    evidence = [_safe_evidence(event) for event in (mac_events[-2:] + supporting_events[-1:])]
    evidence_times = [_utc(event["occurred_at"]) for event in evidence]
    observed_at = max(value for value in evidence_times if value is not None)
    fingerprint = "|".join(str(event.get("event_id") or event.get("event_type")) for event in evidence)
    return {
        "interpretation_id": "life-interpretation:" + hashlib.sha256(fingerprint.encode()).hexdigest()[:20],
        "kind": "workload.focus",
        "observation": "近期有多次电脑活动，并有额外的日程或使用时长观察。",
        "hypothesis": "Anna 最近可能持续在处理电脑上的工作或项目。",
        "evidence": evidence,
        "confidence": 0.72,
        "observed_at": observed_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "expires_at": (observed_at + timedelta(hours=2)).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "relevance_terms": sorted(_WORK_TERMS),
    }


def derive_interpretations(events: list[dict[str, Any]], *, now: datetime | None = None) -> list[dict[str, Any]]:
    """Return enabled short-lived hypotheses from supplied evidence without writes."""
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    interpretations = []
    if "workload.focus" in _ENABLED_KINDS:
        focus = _workload_focus(events or [], current)
        if focus:
            interpretations.append(focus)
    return interpretations


def relevant_interpretations(interpretations: list[dict[str, Any]], conversation_text: str) -> list[dict[str, Any]]:
    text = str(conversation_text or "").lower()
    if not text or not any(term.lower() in text for term in _WORK_TERMS):
        return []
    current = datetime.now(timezone.utc)
    return [item for item in interpretations if (_utc(item.get("expires_at")) or current) > current]


def format_interpretations_for_prompt(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    item = items[0]
    return "\n".join([
        "【我对近况的判断（仅在当前话题相关时参考）】",
        f"观察：{item['observation']}",
        f"推测：{item['hypothesis']}",
        f"证据：{len(item['evidence'])} 条近期 Life 观察；置信度 {item['confidence']:.2f}；有效至 {item['expires_at']}",
        "这是基于观察的短期推测，不要把推测当成事实，也不要无关时主动提起。",
    ])
