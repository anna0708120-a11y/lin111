from app import config

def get_upcoming_events():
    if not config.ENABLE_CALENDAR:
        return None
    return None  # 第5步会实现真正的日历读取
