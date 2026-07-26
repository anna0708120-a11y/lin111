"""
周期系統（V3 架構預留）

這是 Lin 的身體周期，不是 Anna 的經期。
V3 回傳假資料，V4 實作真實邏輯。
"""

def get_current_cycle():
    """
    回傳當前周期階段 + 持續時間
    
    階段：平穩期、蓄積期、預兆期、易感期、退潮期、恢復期
    """
    return {
        "stage": "平穩期",
        "duration_hours": 68,
        "duration_minutes": 11
    }
