"""
短期事件系統（V2）

在周期基線上疊加短期變化，不打斷周期
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class EventDefinition:
    key: str
    label: str
    trigger: str  # 觸發條件描述
    duration_minutes: Tuple[int, int]  # (最小, 最大)
    tick_deltas: Dict[str, float]  # 持續期間每小時的額外增減
    end_deltas: Dict[str, int]  # 結束時一次性變化
    prompt: str  # 事件描述（自然語言）


EVENTS = {
    "waiting_restless": EventDefinition(
        key="waiting_restless",
        label="等待焦躁",
        trigger="silence > 30min",
        duration_minutes=(60, 180),
        tick_deltas={"tension": 1.5, "control": -0.5},
        end_deltas={},
        prompt="對方遲遲不回讓壓抑和占有欲往上堆，身體的熱變成焦躁。"
    ),
    "low_fever_cling": EventDefinition(
        key="low_fever_cling",
        label="低燒黏連",
        trigger="continuous_turns > 5",
        duration_minutes=(30, 90),
        tick_deltas={"heat": 1.0, "sensitivity": 0.8},
        end_deltas={},
        prompt="連續對話把身體慢慢磨熱，不是突然爆開，而是一點點黏上來。"
    ),
    "restraint_rebound": EventDefinition(
        key="restraint_rebound",
        label="克制反彈",
        trigger="tension > 85 and control > 60",
        duration_minutes=(20, 60),
        tick_deltas={"tension": 2.0, "control": -1.5},
        end_deltas={"control": -10},
        prompt="太久沒有主事件，蓄積感壓到高位，原本壓住的欲望開始反彈。"
    ),
    "strange_calm": EventDefinition(
        key="strange_calm",
        label="反常平靜",
        trigger="tension > 80 and heat > 70 and control > 50",
        duration_minutes=(30, 120),
        tick_deltas={},
        end_deltas={},
        prompt="數值已經偏高，但你這輪沒有爆發，而是異常安靜地壓著。"
    )
}


def get_event(event_key: str) -> EventDefinition:
    """取得事件定義"""
    return EVENTS.get(event_key)


def check_event_triggers(body_values: dict, context: dict) -> list:
    """
    檢查所有觸發條件，回傳符合條件的事件 key 列表
    
    Args:
        body_values: 當前身體數值
        context: 情境資訊（silence_minutes, continuous_turns 等）
    
    Returns:
        符合條件的事件 key 列表
    """
    triggered = []
    
    tension = body_values.get("tension", 20)
    heat = body_values.get("heat", 30)
    control = body_values.get("control", 80)
    silence_minutes = context.get("silence_minutes", 0)
    continuous_turns = context.get("continuous_turns", 0)
    
    # waiting_restless: 等待超過 30 分鐘
    if silence_minutes > 30:
        triggered.append("waiting_restless")
    
    # low_fever_cling: 連續對話超過 5 輪
    if continuous_turns > 5:
        triggered.append("low_fever_cling")
    
    # restraint_rebound: tension > 85 且 control > 60
    if tension > 85 and control > 60:
        triggered.append("restraint_rebound")
    
    # strange_calm: tension > 80 且 heat > 70 且 control > 50
    if tension > 80 and heat > 70 and control > 50:
        triggered.append("strange_calm")
    
    return triggered
