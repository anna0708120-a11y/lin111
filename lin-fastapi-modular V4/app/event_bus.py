"""
System Monitor Event Bus - V2

所有背景事件的統一入口。Home UI 只讀這裡，不直接依賴各模組。

Persistent 類型（狀態型）：只保留最後一筆，新資料覆蓋舊資料。
  mac / weather / location / screentime / calendar / app

Activity 類型（事件型）：保留歷史，最多 50 筆。
  initiative / memory / reflection / wake_up / bark / mood_event / system

Rate limit：同類型 Activity 事件 30 秒內只保留最後一次。
"""

from datetime import datetime
from zoneinfo import ZoneInfo

# System Event / Activity 顯示時間固定用香港時區，不依賴 server 系統時區
# （Render 預設跑 UTC，naive datetime.now() 會慢 8 小時）
DISPLAY_TZ = ZoneInfo("Asia/Hong_Kong")

# 狀態型：新資料覆蓋，不堆疊
PERSISTENT_TYPES = {"mac", "weather", "location", "screentime", "calendar", "app"}

# 事件型：保留歷史
ACTIVITY_TYPES = {"initiative", "memory", "reflection", "wake_up", "bark", "mood_event", "system"}

# Activity 事件保留上限
ACTIVITY_MAX = 50

# Rate limit 秒數（同類型 Activity 事件間隔）
RATE_LIMIT_SECONDS = 30


class EventBus:
    def __init__(self):
        # Persistent: {type_key -> event_dict}
        self._persistent: dict = {}
        # Activity: list of event_dict（舊→新）
        self._activity: list = []
        # Rate limit tracker: {type -> datetime}
        self._last_emit: dict = {}

    def emit(self, event_type: str, message: str, level: str = "info"):
        """
        發佈一個事件。

        event_type: 見 PERSISTENT_TYPES / ACTIVITY_TYPES
        message:    人類可讀的訊息文字
        level:      "info" / "warn" / "alert"
        """
        now = datetime.now(DISPLAY_TZ)
        event = {
            "type": event_type,
            "level": level,
            "message": message,
            "time": now.strftime("%H:%M"),
            "timestamp": now.isoformat(),
        }

        if event_type in PERSISTENT_TYPES:
            # 狀態型：直接覆蓋
            self._persistent[event_type] = event

        else:
            # 事件型：Rate limit 檢查
            last = self._last_emit.get(event_type)
            if last and (now - last).total_seconds() < RATE_LIMIT_SECONDS:
                # 同類型太頻繁，更新最後一筆而不是新增
                for i in range(len(self._activity) - 1, -1, -1):
                    if self._activity[i]["type"] == event_type:
                        self._activity[i] = event
                        return
            self._last_emit[event_type] = now
            self._activity.append(event)
            # 超過上限，移除最舊的
            if len(self._activity) > ACTIVITY_MAX:
                self._activity.pop(0)

    def get_snapshot(self) -> dict:
        """
        給 /events 端點用。
        persistent: {type -> event}（最新狀態）
        activity:   最近 20 筆，倒序（最新在前）
        """
        return {
            "persistent": dict(self._persistent),
            "activity": list(reversed(self._activity[-20:])),
        }


# 全局唯一實例
event_bus = EventBus()
