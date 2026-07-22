"""
Context Provider：所有"外部世界数据"的统一大门。
brain.py 不会、也不应该自己去各个模块东拼西凑——
它只会说"我现在需要哪些"，剩下的交给这里。

以后加新来源（App监控、Bark历史、宠物互动...），
只要在这里加一个 case，不用碰 brain.py。
"""
from app.context import calendar as calendar_source
from app.context import location as location_source
from app.context import mac as mac_source
from app.context import screentime as screentime_source
from app.context import weather as weather_source

_SOURCES = {
    "mac": mac_source.get_mac_status,
    "weather": weather_source.get_weather,
    "calendar": calendar_source.get_upcoming_events,
    "screentime": screentime_source.get_screentime,
    "location": location_source.get_latest_location,
}

def get_context(need=None):
    """
    need: 想要哪些来源的列表，例如 ["weather", "screentime"]。
    不传就默认全部尝试（但每个来源内部仍会检查自己的 ENABLE_ 开关）。
    回传格式：{"weather": {...}, "screentime": {...}}，
    如果某来源关闭或抓取失败，直接不出现在结果里（而不是塞一堆 None 进 Prompt）。
    """
    keys = need if need else list(_SOURCES.keys())
    result = {}
    for key in keys:
        fn = _SOURCES.get(key)
        if not fn:
            continue
        try:
            value = fn()
            if value:
                result[key] = value
        except Exception as e:
            print(f"[context.provider] 读取 {key} 失败: {e}")
    return result

def format_context_for_prompt(context_dict):
    """
    把 get_context() 的结果转成一段给 persona.build_system_prompt 用的文字。
    只在有值时才组装对应那一行，不会出现"天气：无"这种废话占 token。
    """
    lines = []
    if "weather" in context_dict:
        w = context_dict["weather"]
        lines.append(f"目前天气：{w.get('temperature')}°C（体感{w.get('feels_like')}°C），湿度{w.get('humidity')}%")
    if "mac" in context_dict:
        m = context_dict["mac"]
        status_bits = []
        if m.get("locked"):
            status_bits.append("锁屏中")
        if m.get("asleep"):
            status_bits.append("睡眠中")
        if m.get("charging"):
            status_bits.append("充电中")
        status_text = "、".join(status_bits) if status_bits else "使用中"
        detail = f"Anna的Mac状态：{status_text}，电量{m.get('battery')}%"
        if m.get("cpu") is not None:
            detail += f"，CPU使用率{m.get('cpu')}%"
        if m.get("ram") is not None:
            detail += f"，内存使用率{m.get('ram')}%"
        lines.append(detail)
    if "calendar" in context_dict:
        events = context_dict["calendar"]
        if events:
            first = events[0]
            lines.append(f"Anna接下来的日程：{first.get('title')}（{first.get('start')}）")
    if "screentime" in context_dict:
        s = context_dict["screentime"]
        total = s.get('total_minutes', 0)
        line = f"Anna今天屏幕使用时间：约{total}分钟"
        # 如果有 app 使用明细,显示前3个
        if s.get('apps') and isinstance(s['apps'], list):
            top_apps = s['apps'][:3]
            app_names = [f"{app.get('name', '未知')}({app.get('minutes', 0)}分钟)" for app in top_apps]
            if app_names:
                line += f"，主要使用：{', '.join(app_names)}"
        lines.append(line)
    if "location" in context_dict:
        loc = context_dict["location"]
        # 优先使用 label,如果没有就用 latitude/longitude
        if loc.get("label"):
            lines.append(f"Anna目前位置：{loc.get('label')}")
        elif loc.get("latitude") is not None and loc.get("longitude") is not None:
            lat = loc.get("latitude")
            lng = loc.get("longitude")
            lines.append(f"Anna目前位置：{lat:.4f}, {lng:.4f}")
    return "\n".join(lines)
