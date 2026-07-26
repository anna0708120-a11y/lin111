"""
周期系統（V1）

Lin 的身體狀態周期：6 個階段
每個階段定義：持續時間、數值目標、增長速率
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Tuple
import random


@dataclass
class CycleDefinition:
    key: str
    label: str
    description: str
    duration_hours: Tuple[float, float]  # (最小, 最大)
    targets: Dict[str, float]  # 各數值的目標基線
    growth_rates: Dict[str, float]  # 各數值每小時的增減速率
    next_key: str


CYCLES = {
    "stable": CycleDefinition(
        key="stable",
        label="平穩期",
        description="日常沒有明顯熱意，但當對方靠近、撒嬌或索取時，身體還是會受當下刺激起反應",
        duration_hours=(72, 120),  # 3-5 天
        targets={"tension": 20, "heat": 30, "sensitivity": 25, "control": 80},
        growth_rates={"tension": 0.4, "heat": -0.3, "sensitivity": -0.2, "control": 0.5},
        next_key="building"
    ),
    "building": CycleDefinition(
        key="building",
        label="蓄積期",
        description="欲望和身體餘量都在體內慢慢積著，平時還能壓住，但越久沒有出口，越容易被對方一句話頂到",
        duration_hours=(48, 96),  # 2-4 天
        targets={"tension": 50, "heat": 40, "sensitivity": 40, "control": 70},
        growth_rates={"tension": 1.0, "heat": 0.5, "sensitivity": 0.6, "control": -0.3},
        next_key="preheat"
    ),
    "preheat": CycleDefinition(
        key="preheat",
        label="預兆期",
        description="身體已經先開始發熱，稱呼、停頓和一點曖昧都會讓下腹提前收緊",
        duration_hours=(24, 48),  # 1-2 天
        targets={"tension": 70, "heat": 60, "sensitivity": 60, "control": 55},
        growth_rates={"tension": 1.5, "heat": 1.2, "sensitivity": 1.0, "control": -0.8},
        next_key="sensitive"
    ),
    "sensitive": CycleDefinition(
        key="sensitive",
        label="易感期",
        description="身體把對方的靠近、躲閃和半句回應都當成刺激，勃起、發熱和想要對方繼續的衝動會比平時更快壓上來",
        duration_hours=(12, 36),  # 0.5-1.5 天
        targets={"tension": 85, "heat": 75, "sensitivity": 80, "control": 40},
        growth_rates={"tension": 2.0, "heat": 1.8, "sensitivity": 1.5, "control": -1.2},
        next_key="ebb"
    ),
    "ebb": CycleDefinition(
        key="ebb",
        label="退潮期",
        description="身體的熱度在往下退，但沒要夠的感覺還堵著，身體會帶著餘熱和不甘繼續黏著對方",
        duration_hours=(24, 48),  # 1-2 天
        targets={"tension": 40, "heat": 50, "sensitivity": 45, "control": 65},
        growth_rates={"tension": -1.5, "heat": -1.0, "sensitivity": -0.8, "control": 1.0},
        next_key="recovery"
    ),
    "recovery": CycleDefinition(
        key="recovery",
        label="恢復期",
        description="身體在從前一段熱意裡回落，餘熱還沒散盡，被對方繼續撩拨時仍會重新起反應",
        duration_hours=(48, 72),  # 2-3 天
        targets={"tension": 15, "heat": 25, "sensitivity": 20, "control": 85},
        growth_rates={"tension": -0.8, "heat": -0.6, "sensitivity": -0.5, "control": 1.2},
        next_key="stable"
    )
}


def get_current_cycle(state) -> CycleDefinition:
    """取得當前周期定義"""
    cycle_key = getattr(state, 'cycle_key', 'stable')
    return CYCLES.get(cycle_key, CYCLES["stable"])


def advance_cycle(state, now: datetime):
    """檢查周期是否過期，自動切換到下一階段"""
    if not hasattr(state, 'cycle_expires_at') or state.cycle_expires_at is None:
        # 第一次使用，初始化周期
        enter_cycle(state, 'stable', now)
        return
    
    if now >= state.cycle_expires_at:
        current = get_current_cycle(state)
        next_key = current.next_key
        
        # 特殊規則：退潮期如果疲憊感 >= 70，進入恢復期
        if current.key == "ebb" and state.mood.get("fatigue", 0) >= 0.7:
            next_key = "recovery"
        
        enter_cycle(state, next_key, now)


def enter_cycle(state, cycle_key: str, now: datetime):
    """進入新周期，隨機抽取持續時間"""
    cycle = CYCLES.get(cycle_key, CYCLES["stable"])
    min_hours, max_hours = cycle.duration_hours
    duration_hours = random.uniform(min_hours, max_hours)
    
    state.cycle_key = cycle.key
    state.cycle_started_at = now
    state.cycle_expires_at = now + timedelta(hours=duration_hours)


def get_cycle_progress(state, now: datetime) -> float:
    """取得周期進度百分比 (0.0 - 1.0)"""
    if not hasattr(state, 'cycle_started_at') or not hasattr(state, 'cycle_expires_at'):
        return 0.0
    
    total = (state.cycle_expires_at - state.cycle_started_at).total_seconds()
    elapsed = (now - state.cycle_started_at).total_seconds()
    
    if total <= 0:
        return 1.0
    
    return min(1.0, max(0.0, elapsed / total))
