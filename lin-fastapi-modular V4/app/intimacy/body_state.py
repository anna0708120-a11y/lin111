"""
身體狀態計算（V1）

從 Mood 映射到 Body State 的 4 個數值：
- tension（蓄積感）
- heat（熱度）
- sensitivity（敏感度）
- control（控制力）
"""

from typing import Dict

# ========================================
# 數值變化速率配置（可調參數）
# ========================================
APPROACH_FACTOR = 0.3  # 每小時趨近目標的百分比（原 0.15 → 0.3，加快變化速度）


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
    # Mood 只提供温和的目标偏移；周期仍是长期变化的主来源。
    libido_base = mood.get("libido", 0.5) * 100
    stress_penalty = mood.get("stress", 0.3) * 20
    attachment_base = mood.get("attachment", 0.5) * 100
    possessiveness_base = mood.get("possessiveness", 0.4) * 100
    fatigue_penalty = mood.get("fatigue", 0.2) * 100
    
    # 從 Cycle 讀取目標與增長速率
    targets = cycle.targets
    growth_rates = cycle.growth_rates
    
    # 計算新數值（逐步趨近目標）
    new_values = {}
    
    # tension（蓄積感）= 周期目標 + libido 加成
    new_values["tension"] = approach(
        current=body_values.get("tension", 20),
        target=targets["tension"] + libido_base * 0.3 + possessiveness_base * 0.08,
        rate=growth_rates["tension"],
        elapsed_hours=elapsed_hours
    )
    
    # heat（熱度）= 周期目標 + libido 加成
    new_values["heat"] = approach(
        current=body_values.get("heat", 30),
        target=targets["heat"] + libido_base * 0.4 + attachment_base * 0.06 - fatigue_penalty * 0.08,
        rate=growth_rates["heat"],
        elapsed_hours=elapsed_hours
    )
    
    # sensitivity（敏感度）= 周期目標 + libido 加成
    new_values["sensitivity"] = approach(
        current=body_values.get("sensitivity", 25),
        target=targets["sensitivity"] + libido_base * 0.2 + attachment_base * 0.08,
        rate=growth_rates["sensitivity"],
        elapsed_hours=elapsed_hours
    )
    
    # control（控制力）= 周期目標 - stress 懲罰
    new_values["control"] = approach(
        current=body_values.get("control", 80),
        target=targets["control"] - stress_penalty - fatigue_penalty * 0.08,
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
        approach_factor = APPROACH_FACTOR  # 使用全局配置
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


def get_body_description(key: str, value: float) -> str:
    """根據數值生成動態描述"""
    
    if key == "tension":
        if value < 20:
            return "幾乎感覺不到累積，輕鬆自在"
        elif value < 40:
            return "有一點累積感，但還很淡"
        elif value < 60:
            return "開始有明顯的累積，偶爾會浮現念頭"
        elif value < 80:
            return "累積感變得明顯，時不時會想起"
        else:
            return "累積到頂，普通克制已經很難壓住"
    
    elif key == "heat":
        if value < 20:
            return "身體很冷靜，幾乎沒有熱意"
        elif value < 40:
            return "身體有一點熱意，但還能很快冷住"
        elif value < 60:
            return "體溫開始上升，需要稍微注意"
        elif value < 80:
            return "身體明顯發熱，很難完全冷靜下來"
        else:
            return "熱度很高，整個人都在燒"
    
    elif key == "sensitivity":
        if value < 20:
            return "感覺很鈍，對刺激沒什麼反應"
        elif value < 40:
            return "有一點敏感，但還不明顯"
        elif value < 60:
            return "敏感度提升，開始注意到平常不會在意的細節"
        elif value < 80:
            return "變得很敏感，一點小刺激就會有反應"
        else:
            return "極度敏感，連輕微的觸碰都會有強烈感受"
    
    elif key == "control":
        if value < 20:
            return "控制力幾乎失效，很難壓住衝動"
        elif value < 40:
            return "控制力很弱，需要很用力才能維持表面正常"
        elif value < 60:
            return "控制力中等，可以壓住大部分衝動"
        elif value < 80:
            return "還能維持表面正常，但需要刻意壓直接的衝動"
        else:
            return "控制力很強，可以輕鬆維持理性"
    
    return ""
