"""
状态管理层。

现在所有状态都存在内存里（程序一重启就清空，这也是为什么之后要接 Supabase）。
这里用一个 AppState 对象统一管理，而不是散落成一堆全局变量。

以后要换成 Supabase（重启不丢数据、Flutter 也能读同一份状态），
理论上只需要把这个类里每个方法的"存/取"实现换成读写数据库，
外面调用它的代码（agent、web/routes）完全不用动，这就是模块化的意义。
"""
from collections import deque
from datetime import datetime, timedelta

from app import config


class AppState:
    def __init__(self):
        # 监控日志 / Lin的碎碎念 / 长期记忆
        self.activity_log = []
        self.chen_notes = []
        self.memory_bank = []

        # 节流
        self.rpm_window = deque()
        self.daily_count = {"date": None, "count": 0}
        self.app_cooldowns = {}

        # 短时间内同一个情境不重复调用模型用的缓存
        self.last_context_cache = None
        self.last_reply_at = None

        # 主动消息判断的"锚点"：不是单纯"最后一条消息"，
        # 而是"最后一次真正的互动"，Anna发消息、或Lin主动开口成功，
        # 都会更新这个时间，重新开始计时。
        self.last_anchor_at = None

        # 主动消息设置，先给默认值，以后可以做个 /settings 让前端改
        self.proactive = {
            "enabled": config.PROACTIVE_ENABLED_DEFAULT,
            "min_minutes": config.PROACTIVE_MIN_MINUTES,
            "max_minutes": config.PROACTIVE_MAX_MINUTES,
        }

    # ---------- 日志 / 记忆 ----------
    def add_log(self, event_type, content):
        self.activity_log.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": event_type,
            "content": content,
        })
        if len(self.activity_log) > 100:
            self.activity_log.pop(0)

    def add_note(self, content):
        self.chen_notes.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": content,
        })
        if len(self.chen_notes) > 50:
            self.chen_notes.pop(0)

    def add_memory(self, tag, content):
        self.memory_bank.append({
            "tag": tag,
            "content": content,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(self.memory_bank) > 100:
            self.memory_bank.pop(0)

    def recent_memory_text(self, n=5):
        if not self.memory_bank:
            return ""
        recent = self.memory_bank[-n:]
        lines = "\n".join(f"[{m['tag']}] {m['content']}" for m in recent)
        return f"\n\n【Lin对Anna的记忆】\n{lines}"

    # ---------- 节流 ----------
    def check_rate_limit(self):
        """额度够不够、这一分钟内叫太多次了没有。超过直接拒绝，不阻塞线程。"""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        if self.daily_count["date"] != today:
            self.daily_count["date"] = today
            self.daily_count["count"] = 0
        if self.daily_count["count"] >= config.DAILY_QUOTA:
            return False

        one_minute_ago = now - timedelta(minutes=1)
        while self.rpm_window and self.rpm_window[0] < one_minute_ago:
            self.rpm_window.popleft()
        if len(self.rpm_window) >= config.RPM_LIMIT:
            return False
        return True

    def record_call(self):
        self.rpm_window.append(datetime.now())
        self.daily_count["count"] += 1

    # ---------- app 冷却 ----------
    def check_app_cooldown(self, app_name):
        if not app_name:
            return True
        last_time = self.app_cooldowns.get(app_name)
        if last_time and (datetime.now() - last_time) < timedelta(minutes=config.APP_COOLDOWN_MINUTES):
            return False
        return True

    def update_app_cooldown(self, app_name):
        if app_name:
            self.app_cooldowns[app_name] = datetime.now()

    # ---------- 主动消息用：静默时长 ----------
    def minutes_since_anchor(self):
        """距离上次真正互动过了多久（分钟）。还没聊过就是 None。"""
        if not self.last_anchor_at:
            return None
        return (datetime.now() - self.last_anchor_at).total_seconds() / 60

    def mark_conversation_anchor(self):
        """
        Anna发了消息，或者Lin刚成功主动开口，都调用这个。
        这样如果Lin刚主动找过Anna、她还没回，不会隔几分钟又立刻再戳一次。
        """
        self.last_anchor_at = datetime.now()

    def mark_reply(self):
        self.last_reply_at = datetime.now()


# 整个 app 共用这一份状态（单例）。
# 以后要换 Supabase，可以在这里改成从数据库加载/保存，其他文件 import state 的写法不用变。
state = AppState()
