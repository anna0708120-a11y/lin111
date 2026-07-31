"""
Mood 自然衰减系统

让情绪随时间自然回归基线，避免数值永久累积。

设计原则：
1. 每个 Mood 有自己的基线值（baseline）
2. 每小时向基线靠近（decay_rate）
3. 纯函数设计，不跨层修改其他系统
4. 可随时关闭
5. 集中配置，未来迁移到统一配置文件

核心定位：
Mood 应该依靠「事件 + 时间自然恢复」来变化，而不是大量互相影响。
"""

from typing import Dict


# ========================================
# V3: 動態 Target System（借鑒 Eventide）
# ========================================
def get_mood_targets(cycle_key: str = "stable") -> Dict[str, float]:
    """
    根據當前周期返回 Mood 目標值（取代固定 baseline）
    
    設計理念：
    - 平穩期：低 libido、中等 attachment
    - 蓄積期：libido 開始上升
    - 易感期：libido、attachment 都偏高
    - 退潮期/恢復期：逐步回落
    
    這讓角色有「今天就是想黏人」的動態感，而不是永遠回到同一個數字。
    """
    targets_by_cycle = {
        "stable": {
            "attachment": 0.6,
            "curiosity": 0.5,
            "social": 0.6,
            "stress": 0.2,
            "fatigue": 0.3,
            "libido": 0.4,
            "possessiveness": 0.3,
        },
        "building": {
            "attachment": 0.65,
            "curiosity": 0.6,
            "social": 0.65,
            "stress": 0.25,
            "fatigue": 0.35,
            "libido": 0.55,
            "possessiveness": 0.35,
        },
        "preheat": {
            "attachment": 0.7,
            "curiosity": 0.65,
            "social": 0.7,
            "stress": 0.3,
            "fatigue": 0.4,
            "libido": 0.65,
            "possessiveness": 0.4,
        },
        "sensitive": {
            "attachment": 0.75,
            "curiosity": 0.7,
            "social": 0.75,
            "stress": 0.35,
            "fatigue": 0.45,
            "libido": 0.75,
            "possessiveness": 0.5,
        },
        "ebb": {
            "attachment": 0.7,
            "curiosity": 0.6,
            "social": 0.65,
            "stress": 0.3,
            "fatigue": 0.5,
            "libido": 0.6,
            "possessiveness": 0.45,
        },
        "recovery": {
            "attachment": 0.65,
            "curiosity": 0.55,
            "social": 0.6,
            "stress": 0.2,
            "fatigue": 0.35,
            "libido": 0.45,
            "possessiveness": 0.35,
        },
    }
    
    return targets_by_cycle.get(cycle_key, targets_by_cycle["stable"])


# ========================================
# Mood 基线配置（未来迁移到 config.py）
# ========================================
MOOD_BASELINES = {
    "attachment": 0.7,      # 依恋感默认 0.7（温暖但不过分依赖）
    "curiosity": 0.5,       # 好奇心默认 0.5（中等）
    "social": 0.6,          # 社交欲默认 0.6（偏喜欢互动）
    "stress": 0.2,          # 压力默认 0.2（轻微压力）
    "fatigue": 0.3,         # 疲惫感默认 0.3（略微疲惫）
    "libido": 0.4,          # 性欲默认 0.4（中低）
    "possessiveness": 0.3,  # 占有欲默认 0.3（轻微）
}

# ========================================
# Mood 衰减速率配置（每小时向基线靠近的速度）
# ========================================
MOOD_DECAY_RATES = {
    "attachment": 0.01,     # 依恋感慢慢回落
    "curiosity": 0.02,      # 好奇心较快回落
    "social": 0.02,         # 社交欲较快回落
    "stress": 0.02,         # 压力较快消退
    "fatigue": 0.015,       # 疲惫感慢慢恢复
    "libido": 0.015,        # 性欲慢慢回落
    "possessiveness": 0.01, # 占有欲慢慢消退
}


def apply_mood_decay(mood: Dict[str, float], elapsed_hours: float, enabled: bool = True, cycle_key: str = "stable") -> Dict[str, float]:
    """
    应用 Mood 自然衰减（纯函数，不修改输入）
    
    使用渐近回归方式：
    delta = (baseline - current) * rate * elapsed_hours
    
    特点：
    - 离基线越远，回归速度越快
    - 接近基线时自动减速
    - 不会越过基线
    
    Args:
        mood: 当前的 Mood 数值（dict）
        elapsed_hours: 经过的小时数
        enabled: 是否启用衰减（方便 A/B Test）
    
    Returns:
        应用衰减后的新 Mood 数值（不修改原 dict）
    """
    # 如果关闭，直接返回原值的副本
    if not enabled:
        return dict(mood)
    
    # 创建新 dict，不修改原值
    result = dict(mood)
    
    # V3: 使用動態 target 取代固定 baseline
    targets = get_mood_targets(cycle_key)
    
    for key, baseline in targets.items():
        if key not in result:
            continue
        
        current = result[key]
        rate = MOOD_DECAY_RATES.get(key, 0.01)
        
        # 计算向基线靠近的变化量（渐近回归）
        # 公式：delta = (baseline - current) * rate * elapsed_hours
        delta = (baseline - current) * rate * elapsed_hours
        
        # 应用变化
        result[key] = current + delta
        
        # Clamp 到 0.0~1.0
        result[key] = max(0.0, min(1.0, result[key]))
    
    return result


def get_decay_summary(mood: Dict[str, float]) -> str:
    """
    生成当前 Mood 与基线的偏离摘要（用于 Debug，非必要）
    
    Args:
        mood: 当前的 Mood 数值
    
    Returns:
        偏离描述文字，若无明显偏离则返回空字串
    """
    deviations = []
    
    # V3: 使用動態 target 取代固定 baseline
    targets = get_mood_targets(cycle_key)
    
    for key, baseline in targets.items():
        if key not in mood:
            continue
        
        current = mood[key]
        diff = current - baseline
        
        # 只显示偏离基线超过 0.15 的项目
        if abs(diff) > 0.15:
            direction = "偏高" if diff > 0 else "偏低"
            deviations.append(f"{key} {direction} ({current:.2f} vs 基线 {baseline:.2f})")
    
    if not deviations:
        return ""
    
    return "【情绪偏离基线】" + "；".join(deviations)
