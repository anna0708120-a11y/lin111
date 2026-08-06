"""
事件日誌系統（V4 實作）

管理時間軸事件記錄。
"""
from datetime import datetime
from app.db import _client as supabase


def log_event(event_type: str, title: str, timestamp: datetime = None, 
              duration_minutes: int = None, detail_text: str = None, 
              metadata: dict = None):
    """
    寫入事件日誌到資料庫
    
    Args:
        event_type: 'cycle' | 'event' | 'settlement'
        title: 事件標題
        timestamp: 事件時間（預設當前時間）
        duration_minutes: 持續時間（僅 event 類型）
        detail_text: 詳細描述（settlement 使用）
        metadata: 額外數據
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    data = {
        "event_type": event_type,
        "title": title,
        "timestamp": timestamp.isoformat(),
    }
    
    if duration_minutes is not None:
        data["duration_minutes"] = duration_minutes
    if detail_text is not None:
        data["detail_text"] = detail_text
    if metadata is not None:
        data["metadata"] = metadata
    
    if supabase is None:
        return
    try:
        supabase.table("intimacy_events").insert(data).execute()
    except Exception as e:
        print(f"❌ 事件日誌寫入失敗: {e}")


def get_current_event():
    """回傳當前事件 + 持續時間"""
    if supabase is None:
        return {
            "event": "無",
            "duration_hours": 0,
            "duration_minutes": 0,
        }
    try:
        result = supabase.table("intimacy_events") \
            .select("*") \
            .eq("event_type", "event") \
            .order("timestamp", desc=True) \
            .limit(1) \
            .execute()
        
        if result.data:
            event = result.data[0]
            hours = event.get("duration_minutes", 0) // 60
            minutes = event.get("duration_minutes", 0) % 60
            return {
                "event": event["title"],
                "duration_hours": hours,
                "duration_minutes": minutes
            }
    except Exception as e:
        print(f"❌ 讀取當前事件失敗: {e}")
    
    return {
        "event": "無",
        "duration_hours": 0,
        "duration_minutes": 0
    }


def get_event_timeline(filter_type="all"):
    """回傳事件時間軸（真實資料）"""
    if supabase is None:
        return []
    try:
        query = supabase.table("intimacy_events").select("*").order("timestamp", desc=True).limit(50)
        
        if filter_type != "all":
            query = query.eq("event_type", filter_type)
        
        result = query.execute()
        
        events = []
        for row in result.data:
            event = {
                "id": f"evt_{row['id']}",
                "type": row["event_type"],
                "title": row["title"],
                "timestamp": row["timestamp"],
            }
            
            if row.get("duration_minutes"):
                event["duration_minutes"] = row["duration_minutes"]
            if row.get("detail_text"):
                event["detail_text"] = row["detail_text"]
            if isinstance(row.get("metadata"), dict):
                event["metadata"] = row["metadata"]
            
            events.append(event)
        
        return events
    except Exception as e:
        print(f"❌ 讀取事件時間軸失敗: {e}")
        return []


def get_recent_events(limit=5):
    """
    回傳最近 N 條事件（別名，供 prompt.py 使用）
    """
    return get_event_timeline(filter_type="all")[:limit]
