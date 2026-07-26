"""
身體狀態計算（V1）

從 Mood 映射到 Body State 的 4 個數值：
- tension（蓄積感）
- heat（熱度）
- sensitivity（敏感度）
- control（控制力）
"""

from typing import Dict


def calculate_body_state(mood: dict, cycle, body_values: dict, elapsed_hours: float) -> Dict[str, float]:
    """
    計算當前身體狀態
    
    Args:
        mood: Mood Engine 的數值（libido, stress, attachment 等）
        cycle: 當前周期定義
        body_values: 目前的身體數值
        elapsed_hours: 自上次計算經過的小時數
    
    Returns:
        更新後的身體數值
    """
    # 從 Mood 讀取基線影響
    libido_base = mood.get("libido", 0.5) * 100
    stress_penalty = mood.get("stress", 0.3) * 20
    
    # 從 Cycle 讀取目標與增長速率
    targets = cycle.targets
    growth_rates = cycle.growth_rates
    
    # 計算新數值（逐步趨近目標）
    new_values = {}
    
    # tension（蓄積感）= 周期目標 + libido 加成
    new_values["tension"] = approach(
        current=body_values.get("tension", 20),
        target=targets["tension"] + libido_base * 0.3,
        rate=growth_rates["tension"],
        elapsed_hours=elapsed_hours
    )
    
    # heat（熱度）= 周期目標 + libido 加成
    new_values["heat"] = approach(
        current=body_values.get("heat", 30),
        target=targets["heat"] + libido_base * 0.4,
        rate=growth_rates["heat"],
        elapsed_hours=elapsed_hours
    )
    
    # sensitivity（敏感度）= 周期目標 + libido 加成
    new_values["sensitivity"] = approach(
        current=body_values.get("sensitivity", 25),
        target=targets["sensitivity"] + libido_base * 0.2,
        rate=growth_rates["sensitivity"],
        elapsed_hours=elapsed_hours
    )
    
    # control（控制力）= 周期目標 - stress 懲罰
    new_values["control"] = approach(
        current=body_values.get("control", 80),
        target=targets["control"] - stress_penalty,
        rate=growth_rates["control"],
        elapsed_hours=elapsed_hours
    )
    
    # clamp 到 0-100
    for key in new_values:
        new_values[key] = max(0, min(100, new_values[key]))
    
    return new_values


def approach(current: float, target: float, rate: float, elapsed_hours: float) -> float:
    """
    數值逐步趨近目標（借鑒 Eventide 的 approach 邏輯）
    
    Args:
        current: 當前數值
        target: 目標數值
        rate: 每小時的變化速率
        elapsed_hours: 經過的小時數
    
    Returns:
        新的數值
    """
    # 計算總變化量
    delta = rate * elapsed_hours
    
    # 如果是趨近型變化（rate 的符號與 (target - current) 同向）
    # 則使用更平滑的趨近公式
    if (target - current) * rate > 0:
        # 平滑趨近：越接近目標，變化越慢
        approach_factor = 0.15  # 每小時趨近 15%
        return current + (target - current) * approach_factor * elapsed_hours
    else:
        # 線性變化
        return current + delta


def get_body_level(value: float) -> str:
    """將數值映射成「低/中低/中/中高/高」"""
    if value < 20:
        return "低"
    elif value < 40:
        return "中低"
    elif value < 60:
        return "中"
    elif value < 80:
        return "中高"
    else:
        return "高"
