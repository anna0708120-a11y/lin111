"""
互動結算系統（V3）

對話結束後，分析互動內容並更新關係
"""

from typing import Dict


def analyze_interaction(user_message: str, lin_reply: str, continuous_turns: int) -> Dict[str, any]:
    """
    分析互動類型與情感
    
    Args:
        user_message: 用戶消息
        lin_reply: Lin 的回覆
        continuous_turns: 連續對話輪數
    
    Returns:
        {
            "interaction_type": "chat" | "argument" | "comfort" | "long_silence",
            "sentiment": "positive" | "negative" | "neutral",
            "turns": int
        }
    """
    combined = (user_message + " " + lin_reply).lower()
    
    # 檢測互動類型
    interaction_type = "chat"  # 預設
    
    # argument: 吵架
    if any(kw in combined for kw in ["生氣", "生气", "討厭", "讨厌", "煩", "烦", "不要", "不想", "fuck", "shit"]):
        interaction_type = "argument"
    
    # comfort: 安慰
    elif any(kw in combined for kw in ["沒事", "没事", "別怕", "别怕", "陪你", "抱抱", "親親", "亲亲", "乖"]):
        interaction_type = "comfort"
    
    # 檢測情感
    sentiment = "neutral"
    
    # positive
    if any(kw in combined for kw in ["喜歡", "喜欢", "愛", "爱", "想你", "謝謝", "谢谢", "哈哈", "😊", "❤️", "🥰"]):
        sentiment = "positive"
    
    # negative
    elif any(kw in combined for kw in ["生氣", "生气", "難過", "难过", "傷心", "伤心", "累", "煩", "烦", "😢", "😭"]):
        sentiment = "negative"
    
    return {
        "interaction_type": interaction_type,
        "sentiment": sentiment,
        "turns": continuous_turns
    }


def settle_interaction(relationship, user_message: str, lin_reply: str, continuous_turns: int):
    """
    對話結束後，結算並更新關係
    
    Args:
        relationship: 當前關係
        user_message: 用戶消息
        lin_reply: Lin 的回覆
        continuous_turns: 連續對話輪數
    
    Returns:
        更新後的關係
    """
    from app.relationship.engine import update_relationship, calculate_relationship_deltas
    
    # 分析互動
    analysis = analyze_interaction(user_message, lin_reply, continuous_turns)
    
    # 計算變化量
    deltas = calculate_relationship_deltas(analysis)
    
    # 更新關係
    return update_relationship(relationship, deltas)
