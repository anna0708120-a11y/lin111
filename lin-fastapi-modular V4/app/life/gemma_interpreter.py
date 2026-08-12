"""Gemma-powered, read-only compression of recent Life evidence."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from app import config

_CACHE: dict[str, Any] = {"key": None, "expires_at": 0.0, "value": None}
_ALLOWED_TYPES = {"mac.active", "mac.unlocked", "mac.idle", "screentime.summary", "calendar.upcoming", "weather.observed", "phone.observed"}


def _compact(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "event_id": event.get("event_id"),
            "event_type": event.get("event_type"),
            "occurred_at": event.get("occurred_at"),
            "confidence": event.get("confidence"),
            "payload": event.get("payload") or {},
        }
        for event in events
        if event.get("event_type") in _ALLOWED_TYPES
    ][-12:]


def _parse(content: str, evidence: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        value = json.loads(content or "{}")
    except (TypeError, ValueError):
        return None
    if not isinstance(value, dict):
        return None
    observation = str(value.get("observation") or "").strip()[:400]
    interpretation = str(value.get("interpretation") or "").strip()[:400]
    evidence_sufficient = bool(value.get("evidence_sufficient"))
    if not observation or not evidence_sufficient or not interpretation:
        return None
    terms = [str(term).strip()[:40] for term in (value.get("relevance_terms") or []) if str(term).strip()][:8]
    try:
        confidence = max(0.0, min(0.8, float(value.get("confidence") or 0)))
    except (TypeError, ValueError):
        confidence = 0.0
    now = datetime.now(timezone.utc)
    return {
        "observation": observation,
        "interpretation": interpretation,
        "evidence_sufficient": True,
        "evidence": evidence,
        "confidence": confidence,
        "observed_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "expires_at": (now + timedelta(hours=2)).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "relevance_terms": terms,
    }


def interpret_life_evidence(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    compact = _compact(events or [])
    if not compact or not config.GEMMA_API_KEY or not config.GEMMA_MODEL:
        return None
    cache_key = hashlib.sha256(json.dumps(compact, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    now = time.monotonic()
    if _CACHE["key"] == cache_key and _CACHE["value"] is not None and now < _CACHE["expires_at"]:
        return _CACHE["value"]
    instruction = (
        "You are a low-cost Life evidence preprocessor. Return JSON only. "
        "Separate verified observation from uncertain interpretation. Never state interpretation as fact. "
        "Deduplicate repeated sensor observations and give relevance terms for when the result may matter in conversation. "
        'Schema: {"observation":"", "interpretation":"", "evidence_sufficient":false, "confidence":0.0, "relevance_terms":[]}. '
        "Set evidence_sufficient false and interpretation empty whenever the evidence does not support a bounded hypothesis."
    )
    try:
        response = requests.post(
            f"{config.GEMMA_BASE_URL}/chat",
            headers={"Authorization": f"Bearer {config.GEMMA_API_KEY}", "Content-Type": "application/json"},
            json={"model": config.GEMMA_MODEL, "stream": False, "format": "json", "options": {"temperature": 0.1, "num_predict": 220}, "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(compact, ensure_ascii=False)},
            ]},
            timeout=config.GEMMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        value = _parse(response.json().get("message", {}).get("content") or "", compact)
        _CACHE.update({"key": cache_key, "value": value, "expires_at": now + 120.0})
        return value
    except requests.RequestException as exc:
        print(f"[gemma_life_interpreter] request failed: {exc}")
        return None


def relevant_life_interpretation(value: dict[str, Any] | None, conversation: str) -> dict[str, Any] | None:
    if not value or not value.get("interpretation"):
        return None
    text = str(conversation or "").lower()
    terms = [term.lower() for term in value.get("relevance_terms") or []]
    return value if terms and any(term in text for term in terms) else None


def format_for_prompt(value: dict[str, Any] | None) -> str:
    if not value:
        return ""
    lines = [
        "【近期 Life 证据整理（辅助，不是事实判断）】",
        f"观察：{value['observation']}",
        f"证据：{len(value.get('evidence') or [])} 条；置信度 {float(value.get('confidence') or 0):.2f}；有效至 {value.get('expires_at')}",
    ]
    if value.get("interpretation"):
        lines.append(f"Gemma 的推测：{value['interpretation']}")
    lines.append("仅在当前话题相关时参考；推测不能当作事实。")
    return "\n".join(lines)
