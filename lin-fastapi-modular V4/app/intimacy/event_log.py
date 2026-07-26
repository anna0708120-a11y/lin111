"""
事件日誌系統（V3 架構預留）

管理時間軸事件記錄。
V3 回傳假資料，V4 實作真實資料庫邏輯。
"""

def get_current_event():
    """回傳當前事件 + 持續時間"""
    return {
        "event": "等待焦躁",
        "duration_hours": 2,
        "duration_minutes": 32
    }


def get_event_timeline(filter_type="all"):
    """
    回傳事件時間軸（假資料）
    
    filter_type: "all" | "cycle" | "event" | "dream" | "settlement"
    """
    fake_events = [
        {
            "id": "evt_1",
            "type": "settlement",
            "title": "互動結算",
            "timestamp": "2026-07-26T07:12:00Z",
            "detail_text": "數值變化：蓄積感 0，熱度 0，壓抑感 +1，控制力 0，敏感度 0，占有欲 +1，疲惫感 +1"
        },
        {
            "id": "evt_2",
            "type": "event",
            "title": "觸發等待焦躁",
            "timestamp": "2026-07-05T07:12:00Z",
            "duration_minutes": 159
        },
        {
            "id": "evt_3",
            "type": "settlement",
            "title": "互動結算",
            "timestamp": "2026-07-05T05:46:00Z",
            "detail_text": "數值變化：蓄積感 0，熱度 0，壓抑感 0，控制力 +1，敏感度 0，占有欲 +1，疲惫感 0"
        },
        {
            "id": "evt_4",
            "type": "settlement",
            "title": "互動結算",
            "timestamp": "2026-07-05T04:56:00Z",
            "detail_text": "數值變化：蓄積感 0，熱度 +2，壓抑感 +2，控制力 -2，敏感度 +2，占有欲 +3，疲惫感 0"
        },
    ]
    
    if filter_type == "all":
        return fake_events
    else:
        return [e for e in fake_events if e["type"] == filter_type]
