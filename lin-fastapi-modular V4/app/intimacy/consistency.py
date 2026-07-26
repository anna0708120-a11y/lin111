"""
身心一致性計算（V1）

Mood + Body 的組合決定行為描述
"""


def render_consistency_prompt(mood: dict, body_values: dict) -> str:
    """
    根據 Mood 和 Body 的組合，生成行為描述
    
    範例：
    - 依戀高 + 控制力高 → "雖然很想靠近，但還能克制住自己"
    - 依戀高 + 控制力低 → "很想靠近，而且今天克制力不太好，可能會更直接一點"
    """
    lines = []
    
    attachment = mood.get("attachment", 0.5)
    possessiveness = mood.get("possessiveness", 0.5)
    stress = mood.get("stress", 0.3)
    control = body_values.get("control", 80)
    tension = body_values.get("tension", 20)
    
    # 依戀 + 控制力的組合
    if attachment > 0.7:
        if control > 70:
            lines.append("雖然很想靠近，但還能克制住自己，不會過於急迫。")
        elif control < 40:
            lines.append("很想靠近，而且今天克制力不太好，可能會更直接一點。")
        else:
            lines.append("想靠近，但有時候會猶豫要不要表達出來。")
    
    # 占有欲 + 蓄積感的組合
    if possessiveness > 0.7 and tension > 70:
        if control > 70:
            lines.append("占有欲很強，但還在克制，不會直接說出來。")
        else:
            lines.append("占有欲很強，而且今天不太想忍了。")
    
    # 壓力 + 控制力的組合
    if stress > 0.6:
        if control > 70:
            lines.append("雖然有點壓力，但還能維持表面正常。")
        elif control < 40:
            lines.append("今天壓力有點大，耐心不太好。")
    
    return "\n".join(lines) if lines else ""
