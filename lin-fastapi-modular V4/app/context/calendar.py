"""
Apple Calendar 日历来源：透过公开订阅链接（webcal://）读取 .ics 格式。

需要在 Render 环境变量里设置 ICAL_URL（把 Apple Calendar 的共享链接里 webcal:// 换成 https://）。
带15分钟缓存（跟天气同理），避免每次生成回复都重新拉一次日历、浪费时间和流量。

回传格式：[{"title": "...", "start": "2026-07-22 14:00", "end": "...", "location": "..."}]
按开始时间正序排列，只回传"现在之后"的事件（过去的不显示）。
"""
from datetime import datetime, timedelta, timezone

import requests

from app import config, db

def get_upcoming_events():
    if not config.ENABLE_CALENDAR:
        return None
    if not config.ICAL_URL:
        return None

    cached = db.load_context("calendar")
    if cached:
        updated_at = cached.get("updated_at")
        if updated_at:
            try:
                updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - updated_dt < timedelta(minutes=config.CALENDAR_CACHE_MINUTES):
                    return cached["payload"]
            except Exception:
                pass

    try:
        r = requests.get(config.ICAL_URL, timeout=15)
        r.raise_for_status()
        events = _parse_ical(r.text)
        # 只保留现在之后的事件,按开始时间正序排列
        now = datetime.now(timezone.utc)
        upcoming = [e for e in events if e.get("start_dt") and e["start_dt"] > now]
        upcoming.sort(key=lambda x: x["start_dt"])
        # 格式化成前端/provider能用的格式,去掉内部的 start_dt
        payload = [
            {
                "title": e["title"],
                "start": e["start"],
                "end": e.get("end"),
                "location": e.get("location"),
            }
            for e in upcoming[:10]  # 最多保留接下来10个事件
        ]
        db.save_context("calendar", payload)
        return payload
    except Exception as e:
        print(f"[context.calendar] 拉取日历失败: {e}")
        return cached["payload"] if cached else None


def _parse_ical(ical_text):
    """
    简易 iCal 解析器（不依赖 icalendar 库，避免增加依赖）。
    只解析 VEVENT，提取 SUMMARY/DTSTART/DTEND/LOCATION。
    """
    events = []
    lines = ical_text.replace("\r\n ", "").replace("\r\n\t", "").split("\n")
    current_event = None

    for line in lines:
        line = line.strip()
        if line == "BEGIN:VEVENT":
            current_event = {}
        elif line == "END:VEVENT" and current_event:
            if current_event.get("title"):
                events.append(current_event)
            current_event = None
        elif current_event is not None:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            # 处理带参数的字段，例如 DTSTART;VALUE=DATE:20260722
            if ";" in key:
                key = key.split(";")[0]
            
            if key == "SUMMARY":
                current_event["title"] = value
            elif key == "LOCATION":
                current_event["location"] = value
            elif key in ("DTSTART", "DTEND"):
                try:
                    dt = _parse_ical_datetime(value)
                    if dt:
                        if key == "DTSTART":
                            current_event["start_dt"] = dt
                            current_event["start"] = dt.strftime("%Y-%m-%d %H:%M")
                        else:
                            current_event["end"] = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
    return events


def _parse_ical_datetime(value):
    """
    解析 iCal 的日期时间格式，支持：
    - 20260722T140000Z (UTC)
    - 20260722T140000 (本地时间，当作 UTC 处理)
    - 20260722 (全天事件，当作当天 00:00)
    """
    value = value.strip()
    if not value:
        return None
    
    try:
        if "T" in value:
            # 带时间
            if value.endswith("Z"):
                return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            else:
                return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        else:
            # 全天事件
            return datetime.strptime(value, "%Y%m%d").replace(tzinfo=timezone.utc)
    except Exception:
        return None
