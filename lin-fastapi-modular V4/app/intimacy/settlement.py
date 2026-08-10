"""Deterministic interaction settlement for the live chat path.

Settlement is deliberately rule-based in Phase 3: it uses the existing interaction
classification, validates a small bounded delta object, and never performs keyword
based release detection or a second model call.
"""
from dataclasses import dataclass
from typing import Dict


BODY_FIELDS = ("tension", "heat", "sensitivity", "control")
RESULTS = {"neutral", "comfort", "argument", "warm_chat"}


@dataclass(frozen=True)
class SettlementResult:
    result: str = "neutral"
    reason: str = ""
    deltas: Dict[str, float] = None


def analyze_interaction(user_message: str, lin_reply: str, continuous_turns: int) -> Dict[str, object]:
    """Classify the completed interaction using the existing conservative rules."""
    combined = (user_message + " " + lin_reply).lower()
    interaction_type = "chat"
    if any(kw in combined for kw in ["生氣", "生气", "討厭", "讨厌", "煩", "烦", "不要", "不想", "fuck", "shit"]):
        interaction_type = "argument"
    elif any(kw in combined for kw in ["沒事", "没事", "別怕", "别怕", "陪你", "抱抱", "親親", "亲亲", "乖"]):
        interaction_type = "comfort"

    sentiment = "neutral"
    if any(kw in combined for kw in ["喜歡", "喜欢", "愛", "爱", "想你", "謝謝", "谢谢", "哈哈", "😊", "❤️", "🥰"]):
        sentiment = "positive"
    elif any(kw in combined for kw in ["生氣", "生气", "難過", "难过", "傷心", "伤心", "累", "煩", "烦", "😢", "😭"]):
        sentiment = "negative"

    return {
        "interaction_type": interaction_type,
        "sentiment": sentiment,
        "turns": int(continuous_turns or 0),
    }


def settle_interaction(relationship, user_message: str, lin_reply: str, continuous_turns: int):
    """Preserve the existing relationship settlement behavior."""
    from app.relationship.engine import calculate_relationship_deltas, update_relationship
    return update_relationship(
        relationship,
        calculate_relationship_deltas(analyze_interaction(user_message, lin_reply, continuous_turns)),
    )


def build_settlement_result(user_message: str, lin_reply: str, continuous_turns: int) -> SettlementResult:
    """Create a small, backend-owned structured settlement from completed chat."""
    analysis = analyze_interaction(user_message, lin_reply, continuous_turns)
    kind = analysis["interaction_type"]
    sentiment = analysis["sentiment"]
    turns = analysis["turns"]

    if kind == "argument":
        return SettlementResult(
            result="argument",
            reason="本輪互動帶有衝突或明顯負面情緒。",
            deltas={"tension": 3, "heat": 1, "sensitivity": 0, "control": -2},
        )
    if kind == "comfort":
        return SettlementResult(
            result="comfort",
            reason="本輪互動以安慰與安撫為主。",
            deltas={"tension": -2, "heat": 0, "sensitivity": 1, "control": 2},
        )
    if sentiment == "positive" and turns >= 2:
        return SettlementResult(
            result="warm_chat",
            reason="本輪互動正向且延續了對話溫度。",
            deltas={"tension": 1, "heat": 1, "sensitivity": 1, "control": 0},
        )
    return SettlementResult(result="neutral", reason="本輪沒有需要額外結算的身體變化。", deltas={})


def normalize_settlement_result(result: SettlementResult, delta_limit: float = 4.0) -> SettlementResult:
    """Validate result enum and clamp only the supported Body State fields."""
    raw_deltas = result.deltas if isinstance(result.deltas, dict) else {}
    deltas = {}
    for key in BODY_FIELDS:
        try:
            value = float(raw_deltas.get(key, 0))
        except (TypeError, ValueError):
            value = 0.0
        deltas[key] = max(-delta_limit, min(delta_limit, value))
    return SettlementResult(
        result=result.result if result.result in RESULTS else "neutral",
        reason=str(result.reason or ""),
        deltas=deltas,
    )


def apply_settlement_result(state, result: SettlementResult) -> Dict[str, object]:
    """Apply validated deltas, persist through the caller, and return audit data."""
    normalized = normalize_settlement_result(result)
    applied = {}
    for key, delta in normalized.deltas.items():
        before = float(state.body_values.get(key, 0))
        after = max(0.0, min(100.0, before + delta))
        state.body_values[key] = after
        applied[key] = round(after - before, 1)
    return {
        "result": normalized.result,
        "reason": normalized.reason,
        "requested_deltas": normalized.deltas,
        "applied_deltas": applied,
    }
