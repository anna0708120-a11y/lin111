"""
親密引擎核心邏輯

計算：
1. 互動意願（每次請求重新計算，不保存）
2. 親密氛圍描述（根據意願 + Mood 生成）
"""

def compute_willingness(mood):
    """
    計算當前互動意願（低/中/高）
    
    依據：
    - 依戀 (attachment)
    - 壓力 (stress)
    - 疲勞 (fatigue)
    - 佔有 (possessiveness)
    """
    score = 0.5  # 基準值
    
    # 依戀提升意願
    score += mood.get("attachment", 0.5) * 0.3
    
    # 佔有提升意願（戀人關係）
    score += mood.get("possessiveness", 0.3) * 0.2
    
    # 壓力降低意願
    score -= mood.get("stress", 0.3) * 0.4
    
    # 疲勞降低意願
    score -= mood.get("fatigue", 0.3) * 0.3
    
    # 分級
    if score < 0.35:
        return "低"
    elif score < 0.65:
        return "中"
    else:
        return "高"


def get_atmosphere(willingness, mood):
    """
    根據互動意願 + Mood 生成親密氛圍描述
    
    映射表（戀人關係預設）：
    """
    # 戀人階段的氛圍映射
    atmosphere_map = {
        "低": [
            "需要空間", "有點累了", "想安靜一下"
        ],
        "中": [
            "有點依偎", "慢慢靠近", "有點害羞"
        ],
        "高": [
            "想撒嬌", "特別黏人", "很想靠近"
        ]
    }
    
    options = atmosphere_map.get(willingness, ["慢慢靠近"])
    
    # 根據 mood 微調選擇
    stress = mood.get("stress", 0.3)
    possessiveness = mood.get("possessiveness", 0.3)
    
    if willingness == "低":
        return options[0] if stress > 0.6 else options[1]
    elif willingness == "中":
        return options[1] if possessiveness < 0.4 else options[0]
    else:
        return options[1] if possessiveness > 0.6 else options[0]


def get_intimacy_state(mood):
    """
    給 API / Prompt 用的統一入口。

    回傳：
    - willingness：互動意願（低/中/高，每次重新計算，不保存）
    - atmosphere：親密氛圍描述（一句話總結）
    - body_state：V2 身體狀態（V1 階段為預留假資料）

    注意：這裡不包含「關係階段」——已依需求移除，
    因為目前設定 Lin 與 Anna 一律是戀人關係，不需要再判斷陌生/熟悉/親近。
    """
    from app.intimacy.body_state import get_body_state

    willingness = compute_willingness(mood)
    atmosphere = get_atmosphere(willingness, mood)
    body_state = get_body_state()

    return {
        "willingness": willingness,
        "atmosphere": atmosphere,
        "body_state": body_state,
    }
