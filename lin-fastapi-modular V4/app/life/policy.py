"""Deterministic policy checks for Phase 7 actions."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .candidates import is_expired
from .contracts import aware_utc


@dataclass(frozen=True)
class PolicyConfig:
    quiet_start_hour: int = 23
    quiet_end_hour: int = 7
    cooldown_minutes: int = 90
    daily_action_budget: int = 3
    followup_cooldown_minutes: int = 180
    max_ignored_streak: int = 2


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    action: str
    reason: str
    defer_until: str | None = None


def _in_quiet_hours(now: datetime, config: PolicyConfig) -> bool:
    hour = now.hour
    if config.quiet_start_hour < config.quiet_end_hour:
        return config.quiet_start_hour <= hour < config.quiet_end_hour
    return hour >= config.quiet_start_hour or hour < config.quiet_end_hour


def evaluate(candidate: dict[str, Any], context: dict[str, Any] | None = None, *, now: datetime | None = None, config: PolicyConfig | None = None) -> PolicyResult:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    config = config or PolicyConfig()
    context = context or {}
    if is_expired(candidate, now):
        return PolicyResult(False, "expired", "candidate_expired")
    if context.get("duplicate_candidate"):
        return PolicyResult(False, "drop", "duplicate_source_event")
    if context.get("daily_action_count", 0) >= config.daily_action_budget:
        return PolicyResult(False, "defer", "daily_action_budget_exhausted")
    if context.get("same_route_last_sent_minutes") is not None and context["same_route_last_sent_minutes"] < config.cooldown_minutes:
        return PolicyResult(False, "defer", "route_cooldown")
    if context.get("last_interaction_minutes") is not None and context["last_interaction_minutes"] < 2 and candidate.get("route") not in {"transactional"}:
        return PolicyResult(False, "defer", "recent_user_interaction")
    if _in_quiet_hours(now, config) and candidate.get("route") not in {"safety_event", "transactional"}:
        return PolicyResult(False, "defer", "quiet_hours")
    if candidate.get("route") == "conversation_followup":
        ignored = int(context.get("ignored_streak") or 0)
        if ignored >= config.max_ignored_streak:
            return PolicyResult(False, "drop", "ignored_streak_limit")
        if context.get("awaiting_reply_since") and context.get("awaiting_reply_minutes", 0) < config.followup_cooldown_minutes:
            return PolicyResult(False, "defer", "awaiting_reply_cooldown")
    return PolicyResult(True, "evaluate", "policy_pass")
