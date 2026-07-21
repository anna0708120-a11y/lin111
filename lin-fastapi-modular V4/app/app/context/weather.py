"""
天气来源：Open-Meteo（免费、不需要申请key）。
带30分钟缓存：读取 context_state 表里 source='weather' 那条记录的 updated_at，
没超过缓存时间就直接用旧的，不重新打 API，省流量也更快。
"""
from datetime import datetime, timedelta, timezone

import requests

from app import config, db

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
                    return cached["payload"]
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
        }
        db.save_context("weather", payload)
        return payload
    except Exception as e:
        print(f"[context.weather] 拉取天气失败: {e}")
        return cached["payload"] if cached else None
