"""
天气来源：Open-Meteo（免费、不需要申请key）。
带30分钟缓存：读取 context_state 表里 source='weather' 那条记录的 updated_at，
没超过缓存时间就直接用旧的，不重新打 API，省流量也更快。
"""
from datetime import datetime, timedelta, timezone

import requests

from app import config, db

# 天气码 → 簡易描述
_WMO = {
    0: "晴天", 1: "大致晴朗", 2: "局部多雲", 3: "陰天",
    45: "霧", 48: "霧凇",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "陣雨", 81: "陣雨", 82: "強陣雨",
    95: "雷雨", 96: "雷雨夾冰雹", 99: "雷雨夾冰雹",
}

def get_weather():
    if not config.ENABLE_WEATHER:
        return None

    cached = db.load_context("weather")
    if cached:
        updated_at = cached.get("updated_at")
        if updated_at:
            try:
                updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - updated_dt < timedelta(minutes=config.WEATHER_CACHE_MINUTES):
                    payload = dict(cached["payload"])
                    payload.setdefault("observed_at", updated_dt.isoformat(timespec="seconds").replace("+00:00", "Z"))
                    return payload
            except Exception:
                pass

    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={config.WEATHER_LAT}&longitude={config.WEATHER_LON}"
            "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
            "&timezone=auto"
        )
        r = requests.get(url, timeout=10)
        data = r.json().get("current", {})
        payload = {
            "temperature": data.get("temperature_2m"),
            "feels_like": data.get("apparent_temperature"),
            "humidity": data.get("relative_humidity_2m"),
            "wind_speed": data.get("wind_speed_10m"),
            "weather_code": data.get("weather_code"),
            "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
        db.save_context("weather", payload)

        # 寫入 Event Bus（Persistent，覆蓋）
        try:
            from app.event_bus import event_bus
            desc = _WMO.get(payload.get("weather_code"), "")
            msg = f"{payload['temperature']}°C"
            if desc:
                msg += f"  {desc}"
            if payload.get("humidity") is not None:
                msg += f"  濕度 {payload['humidity']}%"
            event_bus.emit("weather", msg)
        except Exception:
            pass

        return payload
    except Exception as e:
        print(f"[context.weather] 拉取天气失败: {e}")
        return cached["payload"] if cached else None
