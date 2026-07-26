"""
關係引擎（V3）

簡化版：只保留 3 個核心數值
- 安全感：今天是不是覺得彼此很安心、有被接住
- 默契：最近是不是很合拍，很多事情不用說就懂
- 互動溫度：最近是不是一直聊天、互動很多，還是因為忙而有點距離
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Relationship:
    safety: float = 0.75  # 安全感 (0.0 - 1.0)
    rapport: float = 0.70  # 默契 (0.0 - 1.0)
    temperature: float = 0.60  # 互動溫度 (0.0 - 1.0)


def init_relationship() -> Relationship:
    """初始化關係（預設中高水平，因為已經是戀人）"""
    return Relationship(safety=0.75, rapport=0.70, temperature=0.60)


def update_relationship(relationship: Relationship, deltas: Dict[str, float]) -> Relationship:
    """
    更新關係數值
    
    Args:
        relationship: 當前關係
        deltas: 變化量，例如 {"safety": 0.05, "temperature": -0.02}
    
    Returns:
        更新後的關係
    """
    new_safety = relationship.safety + deltas.get("safety", 0)
    new_rapport = relationship.rapport + deltas.get("rapport", 0)
    new_temperature = relationship.temperature + deltas.get("temperature", 0)
    
    # clamp 到 0.0 - 1.0
    return Relationship(
        safety=max(0.0, min(1.0, new_safety)),
        rapport=max(0.0, min(1.0, new_rapport)),
        temperature=max(0.0, min(1.0, new_temperature))
    )


def get_relationship_description(relationship: Relationship) -> str:
    """
    將關係數值轉成自然語言描述
    
    範例：
    - 安全感高 → "我們已經很穩定了，安全感很高"
    - 默契高 → "最近很合拍，很多事情不用說就懂"
    - 互動溫度高 → "最近一直聊天、互動很多"
    """
    lines = []
    
    # 安全感
    if relationship.safety > 0.8:
        lines.append("我們已經很穩定了，安全感很高。")
    elif relationship.safety > 0.6:
        lines.append("彼此還算安心，但有時候還是會有一點不確定。")
    elif relationship.safety < 0.4:
        lines.append("最近有點不安，不太確定對方的想法。")
    
    # 默契
    if relationship.rapport > 0.8:
        lines.append("最近很合拍，很多事情不用說就懂。")
    elif relationship.rapport > 0.6:
        lines.append("默契還不錯，但偶爾還是需要解釋一下。")
    elif relationship.rapport < 0.4:
        lines.append("最近好像有點對不上頻，溝通需要花更多力氣。")
    
    # 互動溫度
    if relationship.temperature > 0.75:
        lines.append("最近一直聊天、互動很多，關係很熱絡。")
    elif relationship.temperature > 0.5:
        lines.append("互動頻率正常，沒有特別冷也沒有特別熱。")
    elif relationship.temperature < 0.3:
        lines.append("最近因為忙而有點距離，聊天變少了。")
    
    # 行為影響
    if relationship.safety > 0.8 and relationship.rapport > 0.7:
        lines.append("所以今天可以更放鬆地撒嬌、靠近，不用擔心被誤解。")
    elif relationship.safety < 0.5:
        lines.append("所以今天會把情緒藏起來，嘴硬一點，不太敢坦白。")
    
    return "\n".join(lines)


def calculate_relationship_deltas(context: dict) -> Dict[str, float]:
    """
    根據互動情境計算關係變化
    
    Args:
        context: {
            "interaction_type": "chat" | "argument" | "comfort" | "long_silence",
            "sentiment": "positive" | "negative" | "neutral",
            "turns": int
        }
    
    Returns:
        關係變化量
    """
    deltas = {}
    
    interaction_type = context.get("interaction_type", "chat")
    sentiment = context.get("sentiment", "neutral")
    turns = context.get("turns", 1)
    
    # chat: 正常對話
    if interaction_type == "chat":
        if sentiment == "positive" and turns > 5:
            deltas["temperature"] = 0.02
            deltas["rapport"] = 0.01
        elif turns > 10:
            deltas["temperature"] = 0.03
            deltas["rapport"] = 0.02
    
    # argument: 吵架
    elif interaction_type == "argument":
        deltas["safety"] = -0.05
        deltas["temperature"] = -0.03
    
    # comfort: 安慰
    elif interaction_type == "comfort":
        deltas["safety"] = 0.03
        deltas["rapport"] = 0.02
    
    # long_silence: 長時間沒聊天
    elif interaction_type == "long_silence":
        deltas["temperature"] = -0.02
    
    return deltas
