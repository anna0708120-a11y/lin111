"""
互動意願計算（V4）

計算 Lin 此刻對親密互動的意願程度（0-100）
受 Mood + Body + Relationship 共同影響
"""


def calculate_consent(mood: dict, body_values: dict, relationship: dict, recent_context: dict = None) -> float:
    """
    計算當前互動意願
    
    Args:
        mood: Mood Engine 的數值
        body_values: Body State 的數值
        relationship: Relationship 的數值
        recent_context: 最近對話情境（可選）
    
    Returns:
        互動意願分數 (0-100)
    """
    base = 50.0
    
    # 從 Mood 影響
    base += mood.get("attachment", 0.5) * 30  # 依戀高 → 意願高
    base += mood.get("possessiveness", 0.5) * 20  # 占有欲高 → 意願高
    base -= mood.get("stress", 0.3) * 40  # 壓力高 → 意願低
    base -= mood.get("fatigue", 0.3) * 30  # 疲憊高 → 意願低
    
    # 從 Body State 影響
    base += body_values.get("tension", 20) * 0.3  # 蓄積感高 → 意願高
    base += body_values.get("heat", 30) * 0.2  # 熱度高 → 意願高
    base -= body_values.get("control", 80) * 0.15  # 控制力高 → 意願低（還在克制）
    
    # 從 Relationship 影響
    base += relationship.get("safety", 50) * 0.25  # 安全感高 → 意願高
    base += relationship.get("rapport", 50) * 0.15  # 默契高 → 意願高
    base += relationship.get("temperature", 50) * 0.2  # 互動溫度高 → 意願高
    
    # 從最近情境影響（如果有提供）
    if recent_context:
        if recent_context.get("has_intimate_topic"):
            base += 15
        if recent_context.get("user_initiated_intimacy"):
            base += 10
    
    return max(0, min(100, base))


def get_consent_level(value: float) -> str:
    """將 consent 數值映射成「低/中/高」"""
    if value < 30:
        return "低"
    elif value < 60:
        return "中"
    else:
        return "高"


def get_consent_description(value: float, mood: dict, body_values: dict, relationship: dict) -> str:
    """
    生成 consent 的自然語言描述
    
    不是「能不能進入親密對話」的開關，
    而是「Lin 此刻有多想靠近」的描述
    """
    level = get_consent_level(value)
    
    # 根據組合因素生成描述
    attachment = mood.get("attachment", 0.5)
    tension = body_values.get("tension", 20)
    control = body_values.get("control", 80)
    safety = relationship.get("safety", 50)
    
    if value < 30:
        # 低意願：可能因為疲憊、壓力、安全感不足
        if mood.get("fatigue", 0.3) > 0.7:
            return "今天有點累，比較想安靜待著。"
        elif mood.get("stress", 0.3) > 0.6:
            return "今天心情不太好，不太想被碰。"
        elif safety < 40:
            return "還沒有那麼放鬆，需要一點時間。"
        else:
            return "今天不太想靠那麼近。"
    
    elif value < 60:
        # 中等意願：正常狀態
        if control > 70:
            return "想靠近，但還在克制，不會過於急迫。"
        else:
            return "對靠近有一點想法，但不會主動說出來。"
    
    else:
        # 高意願：身體狀態高 + 安全感高
        if tension > 80 and control < 40:
            return "今天很想靠近，而且克制力不太好，可能會更直接一點。"
        elif attachment > 0.8 and safety > 70:
            return "此刻比平時更想靠近，而且很放鬆，不需要顧慮太多。"
        else:
            return "今天比平時更想跟妳親近一點。"
