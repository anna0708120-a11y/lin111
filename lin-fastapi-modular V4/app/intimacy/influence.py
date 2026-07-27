"""
Body State Influence（身體狀態相互影響）V4.2

简单的相互影响机制，让数值之间有轻微连动。

设计原则：
1. 只影响 Body State（不跨层修改 Mood/Relationship/Memory）
2. 可随时关闭（不影响其他模块）
3. 不保存历史（每次 Tick 重新计算）
4. Threshold 抽成常数（易于调整，未来迁移到统一配置）
5. 只顺势推动，不创造情绪
6. 影响幅度极小（让数值像整体，而非独立数字）

核心定位：
Influence 保持"很弱、很稳定、很可预测"。
真正的大变化来自 Cycle、Event、Settlement；
Influence 只负责让 Body State 更有整体感。
"""

from typing import Dict

# ========================================
# Threshold 常数（调整平衡只改这里）
# 未来迁移到 config.py / balance.py / intimacy_settings.py
# ========================================
TENSION_HIGH = 50
TENSION_VERY_HIGH = 70

HEAT_MEDIUM = 50
HEAT_HIGH = 60
HEAT_VERY_HIGH = 70
HEAT_EXTREME = 80

# ========================================
# Influence 强度常数
# ========================================
INFLUENCE_SMALL = 1.0
INFLUENCE_MEDIUM = 2.0


def apply_influence(body_values: Dict[str, float], enabled: bool = True) -> Dict[str, float]:
    """
    应用身体状态之间的相互影响（纯函数，不修改输入）
    
    在 Cycle、Event、Tick 计算完成后，作为最后的小修正。
    
    规则（只有 3 条，单向无循环）：
    1. Tension ↑ → Heat +
    2. Heat ↑ → Sensitivity +
    3. Heat ↑ → Control -
    
    流程：
    Tension
       ↓
      Heat
       ↓
       ├──→ Sensitivity (+)
       └──→ Control (-)
    
    Args:
        body_values: 当前的身体数值（tension, heat, sensitivity, control）
        enabled: 是否启用 Influence（方便 A/B Test 或关闭）
    
    Returns:
        应用影响后的新身体数值（不修改原 dict）
    """
    # 如果关闭，直接返回原值的副本
    if not enabled:
        return dict(body_values)
    
    # 读取当前数值
    tension = body_values.get("tension", 0)
    heat = body_values.get("heat", 0)
    
    # 计算影响修正值（累加）
    deltas = {
        "tension": 0.0,
        "heat": 0.0,
        "sensitivity": 0.0,
        "control": 0.0
    }
    
    # ========================================
    # 规则 1: Tension ↑ → Heat +
    # （蓄积感高时，身体温度微升）
    # ========================================
    if tension >= TENSION_VERY_HIGH:
        deltas["heat"] += INFLUENCE_MEDIUM
    elif tension >= TENSION_HIGH:
        deltas["heat"] += INFLUENCE_SMALL
    
    # ========================================
    # 规则 2: Heat ↑ → Sensitivity +
    # （热度高时，感知变敏锐）
    # ========================================
    if heat >= HEAT_VERY_HIGH:
        deltas["sensitivity"] += INFLUENCE_MEDIUM
    elif heat >= HEAT_MEDIUM:
        deltas["sensitivity"] += INFLUENCE_SMALL
    
    # ========================================
    # 规则 3: Heat ↑ → Control -
    # （热度高时，控制力微降）
    # ========================================
    if heat >= HEAT_EXTREME:
        deltas["control"] -= INFLUENCE_MEDIUM
    elif heat >= HEAT_HIGH:
        deltas["control"] -= INFLUENCE_SMALL
    
    # 应用修正（创建新 dict，不修改原值）
    result = {}
    for key in body_values:
        result[key] = body_values[key] + deltas.get(key, 0.0)
    
    # Clamp 到 0-100
    for key in result:
        result[key] = max(0.0, min(100.0, result[key]))
    
    return result


def get_influence_summary(body_values: Dict[str, float]) -> str:
    """
    生成当前影响的摘要说明（用于 Debug，非必要）
    
    Args:
        body_values: 当前的身体数值
    
    Returns:
        影响描述文字，若无明显影响则返回空字串
    """
    tension = body_values.get("tension", 0)
    heat = body_values.get("heat", 0)
    
    influences = []
    
    # Tension 影响
    if tension >= TENSION_VERY_HIGH:
        influences.append("蓄积感很高，身体开始发热")
    elif tension >= TENSION_HIGH:
        influences.append("蓄积感上升，体温微升")
    
    # Heat 影响
    if heat >= HEAT_EXTREME:
        influences.append("热度极高，敏感度与控制力受影响")
    elif heat >= HEAT_VERY_HIGH:
        influences.append("热度很高，感知变敏锐")
    elif heat >= HEAT_MEDIUM:
        influences.append("热度上升，轻微影响敏感度")
    
    if not influences:
        return ""
    
    return "【连动影响】" + "；".join(influences)
