"""
夢境系統（V4）

直接借鑒 Eventide 的 Dream 系統：
- DreamSeed：夢境種子（從 Memory 提取主題）
- DreamTrigger：夢境觸發判斷
- apply_dream_after_effect：夢後影響
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import List, Optional
import random


@dataclass
class DreamSeed:
    """夢境種子"""
    theme: str  # 夢境主題（從 Memory 提取）
    intensity: str = "medium"  # low / medium / high
    tags: List[str] = None  # 夢境標籤：sweet / anxious / intimate / neutral
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class DreamSettings:
    """夢境設定"""
    enabled: bool = True
    silence_min_minutes: int = 120  # 最少離線時間
    window_start: str = "00:00"  # 夢境時間窗口開始
    window_end: str = "08:30"  # 夢境時間窗口結束
    cooldown_hours: int = 24  # 冷卻時間


def maybe_create_dream_trigger(
    state,
    now: datetime,
    last_message_at: Optional[datetime],
    dream_settings: Optional[DreamSettings] = None
) -> bool:
    """
    檢查是否應該生成夢境
    
    觸發條件：
    1. 在夢境時間窗口（00:00-08:30）
    2. 離線超過最少時間（120min）
    3. 距離上次夢境超過冷卻時間（24h）
    4. 有夢境種子（從 Memory 提取）
    
    Returns:
        是否觸發夢境
    """
    settings = dream_settings or DreamSettings()
    
    if not settings.enabled:
        return False
    
    # 1. 檢查時間窗口
    if not _in_time_window(now, settings.window_start, settings.window_end):
        return False
    
    # 2. 檢查離線時間
    if not last_message_at:
        return False
    
    silence_minutes = (now - last_message_at).total_seconds() / 60.0
    if silence_minutes < settings.silence_min_minutes:
        return False
    
    # 3. 檢查冷卻時間
    if hasattr(state, 'last_dream_at') and state.last_dream_at:
        cooldown_elapsed = (now - state.last_dream_at).total_seconds() / 3600.0
        if cooldown_elapsed < settings.cooldown_hours:
            return False
    
    # 4. 檢查是否有夢境種子
    seed = extract_dream_seed(state)
    if not seed:
        return False
    
    # 5. 根據周期與身體狀態計算概率
    probability = calculate_dream_probability(state)
    
    # 6. 隨機判定
    roll = random.random()
    if roll >= probability:
        return False
    
    # 觸發成功，記錄時間
    state.last_dream_at = now
    state.last_dream_seed = seed
    
    return True


def extract_dream_seed(state) -> Optional[DreamSeed]:
    """
    從 Memory 提取夢境種子
    
    根據 Mood 和 Body State 決定夢境傾向：
    - tension 高 → 親密主題
    - stress 高 → 焦慮主題
    - 其他 → 溫柔主題
    """
    mood = state.mood
    body_values = getattr(state, 'body_values', {})
    
    tension = body_values.get("tension", 20)
    stress = mood.get("stress", 0.3)
    
    # 決定夢境傾向
    if tension > 70:
        theme_keywords = ["親密", "靠近", "想念", "擁抱"]
        intensity = "high"
        tags = ["intimate"]
    elif stress > 0.6:
        theme_keywords = ["焦慮", "不安", "等待", "找不到"]
        intensity = "medium"
        tags = ["anxious"]
    else:
        theme_keywords = ["溫柔", "平靜", "陪伴", "散步"]
        intensity = "low"
        tags = ["sweet"]
    
    # 從 Memory 搜尋匹配的記憶
    memory_bank = state.memory_bank
    if not memory_bank:
        return None
    
    # 簡單搜尋：找到最近包含關鍵字的記憶
    for memory in reversed(memory_bank):  # 從最近的開始找
        content = memory.get("content", "")
        if any(kw in content for kw in theme_keywords):
            theme = f"夢到{content[:50]}"  # 取前 50 字
            return DreamSeed(theme=theme, intensity=intensity, tags=tags)
    
    # 如果沒找到，用預設主題
    default_theme = f"夢到與 Anna 在一起"
    return DreamSeed(theme=default_theme, intensity=intensity, tags=tags)


def calculate_dream_probability(state) -> float:
    """
    計算夢境觸發概率
    
    受周期與身體狀態影響：
    - stable/recovery → 低概率（12%）
    - building/ebb → 中概率（20%）
    - preheat/sensitive → 高概率（32%）
    """
    cycle_key = getattr(state, 'cycle_key', 'stable')
    
    if cycle_key in {"stable", "recovery"}:
        probability = 0.12
    elif cycle_key in {"building", "ebb"}:
        probability = 0.20
    else:  # preheat, sensitive
        probability = 0.32
    
    return min(0.45, probability)


def apply_dream_after_effect(state, tags: List[str]) -> dict:
    """
    根據夢境標籤施加數值變化
    
    標籤：
    - sweet：溫柔（sensitivity +4, pressure -3, fatigue +2）
    - anxious：焦慮（pressure +8, tension +5, control -3）
    - intimate：親密（tension +12, heat +10, sensitivity +6）
    - released：釋放（tension -18, heat -12, pressure -8, fatigue +6）
    
    Returns:
        實際施加的數值變化
    """
    deltas = {"tension": 0, "heat": 0, "sensitivity": 0, "control": 0}
    
    for tag in tags[:3]:  # 最多處理前 3 個標籤
        tag = tag.strip().lower()
        
        if tag == "sweet":
            deltas["sensitivity"] += 4
            deltas["tension"] -= 3
        elif tag == "anxious":
            deltas["tension"] += 5
            deltas["control"] -= 3
        elif tag == "intimate":
            deltas["tension"] += 12
            deltas["heat"] += 10
            deltas["sensitivity"] += 6
        elif tag == "released":
            deltas["tension"] -= 18
            deltas["heat"] -= 12
            deltas["control"] += 8
    
    # 施加變化
    body_values = state.body_values
    for field, delta in deltas.items():
        body_values[field] = max(0, min(100, body_values[field] + delta))
    
    return deltas


def _in_time_window(current: datetime, start: str, end: str) -> bool:
    """檢查是否在時間窗口內"""
    current_time = current.time().replace(second=0, microsecond=0)
    start_time = _parse_time(start)
    end_time = _parse_time(end)
    
    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        # 跨午夜窗口
        return current_time >= start_time or current_time <= end_time


def _parse_time(value: str) -> time:
    """解析時間字串"""
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))
