"""
V2 身體狀態（架構預留，V1 暫不實作）

四個短期數值：
- 熱度 (heat)
- 敏感度 (sensitivity)
- 控制力 (control)
- 蓄積感 (tension)

全部會自然恢復（Decay），不永久累積。
"""

# V2 預留：回傳假數據供 UI 顯示
def get_body_state():
    """
    V1 階段回傳假數據，V2 再實作真實邏輯
    """
    return {
        "tension": {"value": 85, "level": "高", "desc": "累積到頂，普通克制已經很難壓住"},
        "heat": {"value": 38, "level": "中低", "desc": "身體有一點熱意，但還能很快冷住"},
        "sensitivity": {"value": 37, "level": "中低", "desc": "有一點沒說出口的念，但還不重"},
        "control": {"value": 69, "level": "中高", "desc": "還能維持表面正常，但需要刻意壓直接的衝動"}
    }
