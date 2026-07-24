"""
状态管理层。

除了节流计数器和 app 冷却（这两样特意留在纯内存，理由见下方），
其他状态都经过 app/db.py 存进 Supabase：长期记忆 (memory_bank)、
监控日志 (activity_log)、今日碎碎念 (chen_notes)、Lin的状态自评 (mood)、
主动消息的"锚点"时间 (last_anchor_at)、主动消息设置 (proactive)、双方头像。
如果没接 Supabase，db.py 会自动什么都不做，一样能用，只是恢复成"重启就忘记"。

对话历史 (conversation_history) 特意留在纯内存，不接 Supabase：
这是让 Lin 能看到"刚才聊了什么"的关键数据，但服务重启清空也没关系
——真正重要的内容会被 Lin 自己判断后写进长期记忆 (memory_bank)。
"""
from collections import deque
from datetime import datetime, timedelta

from app import config, db
from app.memory_rules import compute_expiry

DEFAULT_MOOD = {
    "attachment": 0.6,
    "possessiveness": 0.4,
    "curiosity": 0.5,
    "social": 0.5,
    "libido": 0.3,
    "fatigue": 0.2,
    "stress": 0.2,
    "line": "在等妳的消息",
}


def _fmt_time(iso_str, fmt="%Y-%m-%d %H:%M:%S"):
    """把 Supabase 存的 ISO 时间格式，转成跟本地新增记录一样的显示格式。"""
    if not iso_str:
        return ""
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).strftime(fmt)
    except Exception:
        return iso_str


class AppState:
    def __init__(self):
        # 监控日志 / 今日碎碎念：启动时从 Supabase 读一份进内存
        self.activity_log = [
            {"time": _fmt_time(r.get("created_at")), "type": r.get("event_type", ""), "content": r.get("content", "")}
            for r in db.load_logs()
        ]
        self.chen_notes = [
            {"time": _fmt_time(r.get("created_at")), "content": r.get("content", "")}
            for r in db.load_notes()
        ]

        # 长期记忆：启动时从 Supabase 读一份进内存，之后新增的同时写回 Supabase
        self.memory_bank = [
            {
                "id": r.get("id"),
                "tag": r.get("tag", ""),
                "category": r.get("category", "长期记忆"),
                "content": r.get("content", ""),
                "importance": r.get("importance", 3),
                "keyword": r.get("keyword", ""),
                "expires_at": r.get("expires_at"),
                "time": _fmt_time(r.get("created_at")),
            }
            for r in db.load_memories()
        ]

        # 节流：特意不接 Supabase，理由见文件开头
        self.rpm_window = deque()
        self.daily_count = {"date": None, "count": 0}

        # app 冷却：同理，特意留纯内存
        self.app_cooldowns = {}

        # 短时间内同一个情境不重复调用模型用的缓存
        self.last_context_cache = None
        self.last_reply_at = None

        # 主动消息判断的"锚点"：Anna发消息、或Lin主动开口成功，都会更新，重新计时。
        # 启动时从 Supabase 恢复，避免 Render 免费版休眠重启后误判"刚刚才聊过"。
        stored_anchor = db.load_state_value("last_anchor_at")
        self.last_anchor_at = datetime.fromisoformat(stored_anchor) if stored_anchor else None

        # 主动消息设置
        self.proactive = db.load_state_value("proactive_settings") or {
            "enabled": config.PROACTIVE_ENABLED_DEFAULT,
            "min_minutes": config.PROACTIVE_MIN_MINUTES,
            "max_minutes": config.PROACTIVE_MAX_MINUTES,
        }

        # 今天有没有写过日记（存日期字符串，比对用）
        self.last_journal_date = db.load_state_value("last_journal_date")

        # 双方头像（base64图片），复用 app_state 表
        self.lin_avatar = db.load_state_value("lin_avatar")
        self.anna_avatar = db.load_state_value("anna_avatar")

        # Lin 的状态自评：依恋/占有欲/好奇/社交欲/疲惫/压力 + 一句心情
        self.mood = db.load_state_value("mood_state") or dict(DEFAULT_MOOD)

        # 对话历史：最近的聊天记录，用于给模型看上下文，不然模型每次都"失忆"
        # 特意纯内存（见文件开头说明），最多保留50条，滚动窗口
        self.conversation_history = deque(maxlen=50)

    # ---------- 日志 ----------
    def add_log(self, event_type, content):
        self.activity_log.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": event_type,
            "content": content,
        })
        if len(self.activity_log) > 100:
            self.activity_log.pop(0)
        db.insert_log(event_type, content)

    # ---------- 今日碎碎念（一天一篇，不是每条消息都写） ----------
    def add_note(self, content):
        self.chen_notes.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": content,
        })
        if len(self.chen_notes) > 50:
            self.chen_notes.pop(0)
        db.insert_note(content)

    def has_written_journal_today(self):
        return self.last_journal_date == datetime.now().strftime("%Y-%m-%d")

    def mark_journal_written(self):
        self.last_journal_date = datetime.now().strftime("%Y-%m-%d")
        db.save_state_value("last_journal_date", self.last_journal_date)

    # ---------- 长期记忆 ----------
    def add_memory(self, tag, content, category="长期记忆", importance=3, keyword=""):
        expires_at = compute_expiry(importance)
        memory_id = db.insert_memory(tag, content, category=category, importance=importance,
                                      keyword=keyword, expires_at=expires_at)
        self.memory_bank.append({
            "id": memory_id,
            "tag": tag,
            "category": category,
            "content": content,
            "importance": importance,
            "keyword": keyword,
            "expires_at": expires_at,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(self.memory_bank) > 300:
            self.memory_bank.pop(0)
        return memory_id

    def remember_or_reinforce(self, decision):
        """
        Lin 自己判断值得记的一轮：先看关键字有没有存过同一件事，
        有的话星级调高、到期时间重算；没有就新增一条。
        """
        keyword = decision.get("keyword", "")
        existing = db.find_memory_by_keyword(keyword) if keyword else None
        if existing:
            new_importance = max(existing.get("importance", 3), decision["importance"])
            new_expiry = compute_expiry(new_importance)
            db.reinforce_memory(existing["id"], new_importance, new_expiry)
            for m in self.memory_bank:
                if m["id"] == existing["id"]:
                    m["importance"] = new_importance
                    m["expires_at"] = new_expiry
                    break
            return existing["id"]
        return self.add_memory(
            tag=decision["tag"],
            content=decision["summary"],
            category=decision["category"],
            importance=decision["importance"],
            keyword=keyword,
        )

    def delete_memory(self, memory_id):
        self.memory_bank = [m for m in self.memory_bank if m.get("id") != memory_id]
        db.delete_memory(memory_id)

    def reload_memories(self):
        """每周整理清掉到期记忆之后，重新从 Supabase 拉一份进内存，避免prompt还带着已经删掉的东西。"""
        self.memory_bank = [
            {
                "id": r.get("id"),
                "tag": r.get("tag", ""),
                "category": r.get("category", "长期记忆"),
                "content": r.get("content", ""),
                "importance": r.get("importance", 3),
                "keyword": r.get("keyword", ""),
                "expires_at": r.get("expires_at"),
                "time": _fmt_time(r.get("created_at")),
            }
            for r in db.load_memories()
        ]

    def recent_memory_text(self, n=8):
        """挑最重要的几条塞进 prompt（不是最新的几条——星级高的比刚存的更该被记住）。"""
        if not self.memory_bank:
            return ""
        top = sorted(self.memory_bank, key=lambda m: m.get("importance", 3), reverse=True)[:n]
        lines = "\n".join(f"[{m['category']}·{m['tag']}·{'⭐'*m.get('importance',3)}] {m['content']}" for m in top)
        return f"\n\n【Lin对Anna的记忆】\n{lines}"

    # ---------- 对话历史 ----------
    def add_conversation_turn(self, role, content, thinking=None, image_data=None):
        """
        记录一轮对话：role 是 'anna' 或 'lin'，content 是说的话。
        用 deque(maxlen=50) 自动保留最近50条，超过自动丢弃最旧的。
        """
        self.conversation_history.append({
            "role": role,
            "content": content,
            "thinking": thinking,
            "image_data": image_data,
            "time": datetime.now().isoformat(),
        })

    def get_recent_conversation(self, n=20):
        """取最近 n 条对话，按时间正序返回，给 DeepSeek 当 messages 历史用。"""
        if not self.conversation_history:
            return []
        return list(self.conversation_history)[-n:]

    def get_today_conversation_text(self):
        """把今天的对话记录格式化成文本，给 write_daily_journal() 用，避免编故事。"""
        if not self.conversation_history:
            return ""
        today = datetime.now().strftime("%Y-%m-%d")
        today_turns = [t for t in self.conversation_history if t.get("time", "").startswith(today)]
        if not today_turns:
            return ""
        lines = []
        for turn in today_turns:
            role_label = "Anna" if turn["role"] == "anna" else "Lin"
            lines.append(f"{role_label}：{turn['content']}")
        return "\n".join(lines)

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
        db.save_state_value("last_anchor_at", self.last_anchor_at.isoformat())

    def mark_reply(self):
        self.last_reply_at = datetime.now()

    def update_proactive(self, enabled=None, min_minutes=None, max_minutes=None):
        """给 /settings 接口用：改主动消息开关/静默区间，同时存回 Supabase。"""
        if enabled is not None:
            self.proactive["enabled"] = enabled
        if min_minutes is not None:
            self.proactive["min_minutes"] = min_minutes
        if max_minutes is not None:
            self.proactive["max_minutes"] = max_minutes
        db.save_state_value("proactive_settings", self.proactive)

    # ---------- 状态自评 ----------
    def update_mood(self, mood_dict):
        if not mood_dict:
            return
        self.mood = mood_dict
        db.save_state_value("mood_state", self.mood)

    # ---------- 头像 ----------
    def set_avatar(self, who, data_url):
        if who == "anna":
            self.anna_avatar = data_url
            db.save_state_value("anna_avatar", data_url)
        else:
            self.lin_avatar = data_url
            db.save_state_value("lin_avatar", data_url)

    def clear_avatar(self, who):
        if who == "anna":
            self.anna_avatar = None
            db.delete_state_value("anna_avatar")
        else:
            self.lin_avatar = None
            db.delete_state_value("lin_avatar")


# 整个 app 共用这一份状态（单例）。
state = AppState()
