"""
主事件系統（V3）

與 Event 的差異：
- Event: 短期事件（1-3小時），疊加在周期上
- Ephemeral: 主事件（瞬間），直接大幅修改數值，會打斷周期

例如：親密互動後，tension 清零、control 恢復、進入恢復期
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class EphemeralEvent:
    key: str
    label: str
    trigger: str
    immediate_deltas: Dict[str, int]  # 瞬間修改數值
    force_cycle: Optional[str]  # 強制切換周期（例如 "recovery"）
    after_effect_key: Optional[str]  # 觸發的餘波模板
    description: str


EPHEMERAL_EVENTS = {
    "intimacy_release": EphemeralEvent(
        key="intimacy_release",
        label="親密釋放",
        trigger="explicit intimate interaction",
        immediate_deltas={"tension": -70, "heat": -40, "control": +20},
        force_cycle="recovery",
        after_effect_key="post_intimacy",
        description="身體的蓄積和熱度一次性釋放，進入恢復期。"
    ),
    "argument_spike": EphemeralEvent(
        key="argument_spike",
        label="爭吵爆發",
        trigger="heated argument",
        immediate_deltas={"tension": +30, "control": -20, "heat": +10},
        force_cycle=None,
        after_effect_key="post_argument",
        description="吵架讓壓力瞬間升高，克制力下降。"
    ),
    "deep_comfort": EphemeralEvent(
        key="deep_comfort",
        label="深度安慰",
        trigger="emotional comfort scene",
        immediate_deltas={"tension": -15, "control": +10},
        force_cycle=None,
        after_effect_key=None,
        description="被安慰後，壓力稍微緩解。"
    )
}


def trigger_ephemeral_event(state, event_key: str, now):
    """
    觸發主事件
    
    Args:
        state: 全局狀態
        event_key: 事件 key
        now: 當前時間
    """
    from app.intimacy.cycle import enter_cycle
    from app.intimacy.after_effect import create_after_effect
    
    event = EPHEMERAL_EVENTS.get(event_key)
    if not event:
        return
    
    # 1. 瞬間修改數值
    for field, delta in event.immediate_deltas.items():
        state.body_values[field] = state.body_values.get(field, 0) + delta
    
    # clamp 到 0-100
    for key in state.body_values:
        state.body_values[key] = max(0, min(100, state.body_values[key]))
    
    # 2. 強制切換周期
    if event.force_cycle:
        enter_cycle(state, event.force_cycle, now)
    
    # 3. 觸發餘波
    if event.after_effect_key:
        after_effect = create_after_effect(event.after_effect_key, now)
        if after_effect:
            if not hasattr(state, 'active_after_effects'):
                state.active_after_effects = []
            state.active_after_effects.append(after_effect)


def should_trigger_intimacy_release(user_message: str, lin_reply: str, body_values: dict) -> bool:
    """
    檢測是否該觸發親密釋放
    
    條件：
    1. 對話內容明顯包含親密互動
    2. tension > 70 或 heat > 70
    """
    combined = (user_message + " " + lin_reply).lower()
    
    # 檢測親密關鍵詞
    intimacy_keywords = [
        "做愛", "做爱", "性愛", "性爱", "親密", "亲密",
        "進來", "进来", "裡面", "里面", "射", "高潮",
        "舔", "吸", "含", "插", "操"
    ]
    
    has_intimacy = any(kw in combined for kw in intimacy_keywords)
    
    # 檢測數值條件
    tension = body_values.get("tension", 0)
    heat = body_values.get("heat", 0)
    
    return has_intimacy and (tension > 70 or heat > 70)
