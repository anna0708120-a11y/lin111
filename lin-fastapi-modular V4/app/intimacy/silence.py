"""
等待焦躁檢測（V2）

檢測對方多久沒回覆，觸發等待焦躁事件
"""

from datetime import datetime


def detect_silence(last_message_at: datetime, now: datetime) -> dict:
    """
    檢測等待時長
    
    Args:
        last_message_at: 對方最後發消息的時間
        now: 當前時間
    
    Returns:
        {
            "silence_minutes": int,
            "should_trigger_waiting": bool
        }
    """
    if not last_message_at:
        return {"silence_minutes": 0, "should_trigger_waiting": False}
    
    silence_seconds = (now - last_message_at).total_seconds()
    silence_minutes = silence_seconds / 60.0
    
    # 超過 30 分鐘觸發等待焦躁
    should_trigger = silence_minutes > 30
    
    return {
        "silence_minutes": int(silence_minutes),
        "should_trigger_waiting": should_trigger
    }


def calculate_silence_pressure(silence_minutes: int) -> dict:
    """
    根據等待時長計算額外的數值變化
    
    借鑒 Eventide 的 _apply_silence_effects
    
    Returns:
        數值增減量
    """
    if silence_minutes < 30:
        return {}
    
    deltas = {}
    
    if silence_minutes < 60:
        # 30-60 分鐘
        deltas["tension"] = 0.8
        deltas["control"] = 0.0
    elif silence_minutes < 120:
        # 60-120 分鐘
        deltas["tension"] = 1.5
        deltas["control"] = 0.0
    else:
        # >= 120 分鐘
        deltas["tension"] = 2.0
        deltas["control"] = -0.6
    
    return deltas
