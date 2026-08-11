"""Independent Life Runtime delivery path for proactive chat messages."""
from __future__ import annotations

from datetime import datetime, timezone

from app.agent.brain import generate_reply
from app.life.contracts import LifeEvent, iso_utc
from app.life.runtime import ingest_events
from app.state import state

_NON_DELIVERABLE_REPLIES = {
    "信号不好。",
    "今天额度用完了，或者刚刚问太快了，等一下再说。",
}


def _prompt(candidate: dict) -> str:
    snapshot = candidate.get("context_snapshot") or {}
    seed = str(snapshot.get("message_seed") or "")
    route = str(candidate.get("route") or "life_followup")
    return (
        f"这是 Lin 的一次经过允许的主动联系。触发原因：{seed}。路线：{route}。"
        "请用自然、简短、不过度打扰的方式主动发一条消息；"
        "不要提及系统、候选、事件、策略或内部状态。"
    )


def _existing_message(candidate: dict) -> dict | None:
    candidate_id = candidate.get("candidate_id")
    for turn in reversed(state.get_recent_conversation(n=200)):
        trace = turn.get("trace") or {}
        if trace.get("life_candidate_id") == candidate_id:
            return {"message": turn.get("content", ""), "route": candidate.get("route"), "deduplicated": True}
    return None


def deliver_message(candidate: dict) -> dict:
    """Generate and persist one authorized proactive Lin message."""
    existing = _existing_message(candidate)
    if existing:
        return existing
    reply, thinking = generate_reply(_prompt(candidate), use_cache=False)
    text = str(reply or "").strip()
    if not text or text in _NON_DELIVERABLE_REPLIES:
        raise RuntimeError("proactive_message_generation_failed")
    if text == "不发":
        raise RuntimeError("proactive_message_declined")

    state.add_conversation_turn("lin", text, thinking=thinking, trace={"life_candidate_id": candidate.get("candidate_id"), "life_route": candidate.get("route")})
    state.mark_conversation_anchor()
    state.add_log("Life 主动联系", text[:120])
    now = iso_utc(datetime.now(timezone.utc))
    ingest_events([LifeEvent(
        event_id=f"life_message:{candidate['candidate_id']}",
        event_type="life.proactive_message_sent",
        source="life_runtime",
        occurred_at=now,
        received_at=now,
        payload={"candidate_id": candidate.get("candidate_id"), "route": candidate.get("route"), "message": text},
        confidence=1.0,
        dedupe_key=f"life.proactive_message_sent:{candidate['candidate_id']}",
    )])
    return {"message": text, "route": candidate.get("route")}
