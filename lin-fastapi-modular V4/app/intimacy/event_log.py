"""
事件日誌系統（V4 實作）

管理時間軸事件記錄。
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from app.db import _client as supabase


@dataclass
class EventRecord:
    id: Optional[int]
    event_type: str
    title: str
    timestamp: datetime
    duration_minutes: Optional[int] = None
    detail_text: Optional[str] = None
    metadata: Optional[dict] = None


def _deserialize_event(row: dict) -> EventRecord:
    timestamp = datetime.fromisoformat(str(row["timestamp"]).replace("Z", "+00:00"))
    return EventRecord(
        id=row.get("id"),
        event_type=row["event_type"],
        title=row["title"],
        timestamp=timestamp,
        duration_minutes=row.get("duration_minutes"),
        detail_text=row.get("detail_text"),
        metadata=row.get("metadata") if isinstance(row.get("metadata"), dict) else None,
    )


def _load_events(filter_type="all", limit=50):
    if supabase is None:
        return []

    try:
        query = supabase.table("intimacy_events").select("*").order("timestamp", desc=True).limit(limit)
        if filter_type != "all":
            query = query.eq("event_type", filter_type)
        result = query.execute()
        return [_deserialize_event(row) for row in result.data]
    except Exception as e:
        print(f"❌ 讀取事件時間軸失敗: {e}")
        return []


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
        events = _load_events(filter_type="event", limit=1)
        if events:
            event = events[0]
            hours = (event.duration_minutes or 0) // 60
            minutes = (event.duration_minutes or 0) % 60
            return {
                "event": event.title,
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
    """回傳 API 時間軸使用的 JSON-safe event dictionaries。"""
    return [
        {
            "id": f"evt_{event.id}",
            "type": event.event_type,
            "title": event.title,
            "timestamp": event.timestamp.isoformat(),
            **({"duration_minutes": event.duration_minutes} if event.duration_minutes else {}),
            **({"detail_text": event.detail_text} if event.detail_text else {}),
            **({"metadata": event.metadata} if event.metadata else {}),
        }
        for event in _load_events(filter_type=filter_type)
    ]


def get_recent_events(limit=5):
    """回傳 prompt 使用的反序列化 EventRecord 物件。"""
    return _load_events(filter_type="all", limit=limit)
