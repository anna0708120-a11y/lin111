"""
親密引擎核心：互動意願 + 親密氛圍計算
讀取 Mood，不修改 Mood
"""

def compute_willingness(mood):
    """
    計算互動意願（每次回覆前重新計算，不保存）
    
    Args:
        mood: dict，來自 state.mood，包含依戀/佔有/壓力/疲勞等
    
    Returns:
        str: "低" / "中" / "高"
    """
    score = 0.5  # 基準值
    
    # 正向因素
    score += mood.get("attachment", 0.5) * 0.3      # 依戀提升意願
    score += mood.get("possessiveness", 0.3) * 0.2  # 佔有欲提升意願
    
    # 負向因素
    score -= mood.get("stress", 0.3) * 0.4          # 壓力降低意願
    score -= mood.get("fatigue", 0.3) * 0.3         # 疲勞降低意願
    
    # 邊界處理
    score = max(0.0, min(1.0, score))
    
    if score < 0.4:
        return "低"
    elif score < 0.7:
        return "中"
    else:
        return "高"


def get_atmosphere(willingness):
    """
    根據互動意願生成親密氛圍描述
    
    Args:
        willingness: str，"低" / "中" / "高"
    
    Returns:
        str: 氛圍描述（保持距離/慢慢靠近/有點依偎/有點害羞/想撒嬌/有點忍耐/特別黏人）
    """
    # 關係固定為戀人，所以只看互動意願
    atmosphere_map = {
        "低": "有點忍耐",      # 戀人關係但意願低 → 需要空間
        "中": "有點害羞",      # 中等意願 → 溫和狀態
        "高": "特別黏人",      # 高意願 → 主動親密
    }
    return atmosphere_map.get(willingness, "慢慢靠近")


def get_intimacy_state(mood):
    """
    獲取完整的親密狀態（V1：只有互動意願 + 氛圍）
    
    Args:
        mood: dict，來自 state.mood
    
    Returns:
        dict: {
            "willingness": str,       # "低" / "中" / "高"
            "atmosphere": str,        # 氛圍描述
            "body_state": dict        # V2 預留，V1 返回模擬數據
        }
    """
    willingness = compute_willingness(mood)
    atmosphere = get_atmosphere(willingness)
    
    # V2 預留：身體狀態（V1 先返回固定/隨機值供 UI 展示）
    body_state = {
        "heat": 0.38,          # 熱度（0-1）
        "sensitivity": 1.0,    # 敏感度（0-1）
        "control": 0.69,       # 控制力（0-1）
        "tension": 0.37,       # 蓄積感（0-1）
    }
    
    return {
        "relationship": "戀人",  # 固定
        "willingness": willingness,
        "atmosphere": atmosphere,
        "body_state": body_state,
    }
