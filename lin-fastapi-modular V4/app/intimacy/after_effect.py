"""
事件餘波系統（V2）

事件結束後不直接恢復，而是有「餘溫」
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict


@dataclass
class AfterEffect:
    source_event: str  # 來源事件
    duration_minutes: int  # 持續時間
    deltas_per_hour: Dict[str, float]  # 每小時的數值變化
    description: str  # 自然語言描述
    started_at: datetime  # 開始時間
    expires_at: datetime  # 結束時間


AFTER_EFFECT_TEMPLATES = {
    "post_intimacy": {
        "duration_minutes": 40,
        "deltas_per_hour": {"heat": 5, "sensitivity": 8, "control": -3},
        "description": "身體還留著剛才的感覺，熱度慢慢退，但敏感度還在。"
    },
    "post_argument": {
        "duration_minutes": 60,
        "deltas_per_hour": {"tension": 3, "control": 5},
        "description": "雖然已經和好了，但還有一點緊繃感，說話會比平時更小心。"
    },
    "post_waiting": {
        "duration_minutes": 30,
        "deltas_per_hour": {"tension": 2, "control": -2},
        "description": "剛等了很久，還有一點焦躁感沒完全消下去。"
    }
}


def create_after_effect(source_event: str, now: datetime) -> AfterEffect:
    """
    根據事件創建餘波
    
    Args:
        source_event: 來源事件 key
        now: 當前時間
    
    Returns:
        AfterEffect 物件，如果沒有對應模板則回傳 None
    """
    template = AFTER_EFFECT_TEMPLATES.get(source_event)
    if not template:
        return None
    
    duration_minutes = template["duration_minutes"]
    
    return AfterEffect(
        source_event=source_event,
        duration_minutes=duration_minutes,
        deltas_per_hour=template["deltas_per_hour"],
        description=template["description"],
        started_at=now,
        expires_at=now + timedelta(minutes=duration_minutes)
    )


def apply_after_effects(body_values: dict, after_effects: list, elapsed_hours: float) -> dict:
    """
    將所有有效的餘波疊加到數值上
    
    Args:
        body_values: 當前身體數值
        after_effects: 餘波列表
        elapsed_hours: 經過的小時數
    
    Returns:
        更新後的數值
    """
    new_values = dict(body_values)
    
    for effect in after_effects:
        for field, rate in effect.deltas_per_hour.items():
            new_values[field] = new_values.get(field, 0) + rate * elapsed_hours
    
    # clamp 到 0-100
    for key in new_values:
        new_values[key] = max(0, min(100, new_values[key]))
    
    return new_values


def cleanup_expired_effects(after_effects: list, now: datetime) -> list:
    """
    清理過期的餘波
    
    Returns:
        仍然有效的餘波列表
    """
    return [e for e in after_effects if e.expires_at > now]
