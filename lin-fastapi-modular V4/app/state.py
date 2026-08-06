"""
状态管理层。

除了节流计数器和 app 冷却（这两样特意留在纯内存，理由见下方），
其他状态都经过 app/db.py 存进 Supabase：长期记忆 (memory_bank)、
监控日志 (activity_log)、今日碎碎念 (chen_notes)、Lin的状态自评 (mood)、
主动消息的"锚点"时间 (last_anchor_at)、主动消息设置 (proactive)、双方头像。
如果没接 Supabase，db.py 会自动什么都不做，一样能用，只是恢复成"重启就忘记"。

对话历史 (conversation_history) 现在也经过 app/db.py 存进 Supabase 的
conversation_history 表，让手机 dock / 电脑 dock / 网页版三端能读到同一份聊天记录，
不再各自锁在浏览器自己的 localStorage 里。保留条数由 config.CHAT_HISTORY_LIMIT 控制。
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
                "created_by": r.get("created_by", "user"),
                "archived": r.get("archived", False),
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
        stored_mood = db.load_state_value("mood_state")
        print(f"[mood] 读取 mood_state: {stored_mood!r}")
        self.mood = stored_mood or dict(DEFAULT_MOOD)

        # 对话历史：最近的聊天记录，用于给模型看上下文，不然模型每次都"失忆"
        # 启动时从 Supabase 读一份进内存，让三端（手机/电脑/网页）打开时看到同一份记录；
        # 之后新增的同时写回 Supabase。保留条数上限优先从 Supabase 读取用户配置。
        
        # 读取用户配置的聊天记录数量（优先 Supabase，fallback 到环境变量）
        cached_config = db.load_context("chat_config")
        if cached_config and cached_config.get("payload") and cached_config["payload"].get("limit"):
            chat_limit = cached_config["payload"]["limit"]
        else:
            chat_limit = config.CHAT_HISTORY_LIMIT
        
        self.conversation_history = deque(
            (
                {
                    "id": r.get("id"),
                    "role": r.get("role", ""),
                    "content": r.get("content", ""),
                    "thinking": r.get("thinking"),
                    "image_data": r.get("image_data"),
                    "time": r.get("time") or r.get("created_at", ""),
                    "trace": r.get("trace"),
                }
                for r in db.load_conversations(limit=chat_limit)
            ),
            maxlen=chat_limit,
        )
        
        # Intimacy Engine 狀態（V1 新增）
        self.cycle_key = "stable"
        self.cycle_started_at = None
        self.cycle_expires_at = None
        self.body_values = {"tension": 20, "heat": 30, "sensitivity": 25, "control": 80}
        self.last_tick_at = None
        
        # V2 新增
        self.active_event_key = None
        self.active_event_started_at = None
        self.active_event_expires_at = None
        self.active_after_effects = []  # List[AfterEffect]
        self.continuous_turns = 0  # 連續對話輪數
        self.last_user_message_at = None  # 用戶最後發消息時間

        # Phase 1: reuse the existing app_state key-value storage for recovery.
        # A missing or invalid snapshot keeps the previous first-run defaults.
        self._load_body_state_snapshot()
        
        # V3 新增：Relationship Engine
        from app.relationship.engine import init_relationship
        self.relationship = init_relationship()
        
        # V4 新增：Dream
        self.last_dream_at = None
        self.last_dream_seed = None
        
        # V4.1 新增：Dream History
        from app.intimacy.dream_history import DreamHistory
        self.dream_history = DreamHistory(max_records=10)
        
        # V4.1 新增：Consent Dynamics
        from app.intimacy.consent_dynamics import ConsentDynamics
        self.consent_dynamics = ConsentDynamics()
        
        # 多聊天室支持（参考 Claude 界面）
        from app import session as session_module
        self.current_session_id = session_module.get_default_session()
        # 每个 session 有自己的对话历史缓存
        self.session_conversations = {}  # {session_id: deque([...])}
        # 加载当前 session 的对话历史
        self._load_session_conversations(self.current_session_id)

    # ---------- 日志 ----------
    # ---------- 多聊天室管理 ----------
    def _load_session_conversations(self, session_id):
        """加载指定 session 的对话历史到缓存"""
        if session_id in self.session_conversations:
            self.conversation_history = self.session_conversations[session_id]
            print("[CHAT-ID-3]", id(self.conversation_history))
            return
        
        # 从数据库加载
        cached_config = db.load_context("chat_config")
        if cached_config and cached_config.get("payload") and cached_config["payload"].get("limit"):
            chat_limit = cached_config["payload"]["limit"]
        else:
            chat_limit = config.CHAT_HISTORY_LIMIT
        
        conversations = deque(
            (
                {
                    "id": r.get("id"),
                    "role": r.get("role", ""),
                    "content": r.get("content", ""),
                    "thinking": r.get("thinking"),
                    "image_data": r.get("image_data"),
                    "time": r.get("time") or r.get("created_at", ""),
                    "trace": r.get("trace"),
                }
                for r in db.load_conversations(limit=chat_limit, session_id=session_id)
            ),
            maxlen=chat_limit,
        )
        
        self.session_conversations[session_id] = conversations
        self.conversation_history = conversations
        print("[CHAT-ID-3]", id(self.conversation_history))
    
    def switch_session(self, session_id):
        """切换到指定的聊天室"""
        self.current_session_id = session_id
        self._load_session_conversations(session_id)
    
    def create_new_session(self):
        """创建新聊天室并切换过去"""
        from app import session as session_module
        new_session = session_module.create_new_session()
        self.switch_session(new_session["id"])
        return new_session
    
    # ---------- 日志 ----------
    # ---------- 聊天记录配置 ----------
    def update_chat_history_limit(self, new_limit: int):
        """动态更新聊天记录保留数量"""
        # 将现有记录转为列表
        existing = list(self.conversation_history)
        # 只保留最新的 new_limit 条
        if len(existing) > new_limit:
            existing = existing[-new_limit:]
        # 重新创建 deque
        self.conversation_history = deque(existing, maxlen=new_limit)
        # 保存配置到 Supabase
        from app import db
        db.save_context("chat_config", {"limit": new_limit})

    def add_log(self, event_type, content):
        # Activity Log 顯示時間固定用香港時區，不依賴 server 系統時區
        # （Render 預設跑 UTC，naive datetime.now() 會慢 8 小時）
        from zoneinfo import ZoneInfo
        self.activity_log.append({
            "time": datetime.now(ZoneInfo("Asia/Hong_Kong")).strftime("%Y-%m-%d %H:%M:%S"),
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
    def add_memory(self, tag, content, category="长期记忆", importance=3, keyword="", created_by="user"):
        expires_at = compute_expiry(importance)
        memory_id = db.insert_memory(tag, content, category=category, importance=importance,
                                      keyword=keyword, expires_at=expires_at, created_by=created_by)
        self.memory_bank.append({
            "id": memory_id,
            "tag": tag,
            "category": category,
            "content": content,
            "importance": importance,
            "keyword": keyword,
            "expires_at": expires_at,
            "created_by": created_by,
            "archived": False,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(self.memory_bank) > 300:
            self.memory_bank.pop(0)
        return memory_id

    def remember_or_reinforce(self, decision):
        """
        Lin 自己判断值得记的一轮：先看关键字有没有存过同一件事，
        有的话星级调高、到期时间重算；没有就新增一条。
        
        Phase 1: 加入 keyword normalization 和 conflict detection
        """
        from app.keyword_normalizer import normalize_keyword
        from app.memory_conflict import detect_conflict, handle_memory_with_conflict_check
        
        raw_keyword = decision.get("keyword", "")
        
        # Phase 1: 使用衝突檢查邏輯
        result = handle_memory_with_conflict_check(decision)
        
        # 同步到內存（只有非 pending_review 的才加入）
        if result["memory_id"] and result["action_taken"] != "pending_review":
            normalized_keyword = normalize_keyword(raw_keyword)
            
            if result["action_taken"] == "reinforced":
                # 更新內存中的記憶
                for m in self.memory_bank:
                    if m.get("id") == result["memory_id"]:
                        m["importance"] = decision["importance"]
                        m["expires_at"] = compute_expiry(decision["importance"])
                        break
            else:
                # 新建記憶加入內存
                self.memory_bank.append({
                    "id": result["memory_id"],
                    "tag": decision["tag"],
                    "category": decision["category"],
                    "content": decision["summary"],
                    "importance": decision["importance"],
                    "keyword": normalized_keyword,
                    "expires_at": compute_expiry(decision["importance"]),
                    "created_by": "agent",
                })
                if len(self.memory_bank) > 300:
                    self.memory_bank.pop(0)
        
        return result  # Phase 2: 回傳完整 result 供 trace 使用

    def update_memory(self, decision):
        """
        Lin 判断"同一件事已经变化"：只能更新自己建立的记忆（created_by=agent），
        找不到符合条件的对象（keyword没命中，或命中的是Anna手动建的）就转为新增一条，
        不去动Anna手动建立的记忆。
        
        Phase 1: 如果內容差異大，視為衝突 -> pending_review
        """
        from app.keyword_normalizer import normalize_keyword
        from app.memory_conflict import _content_similarity
        
        raw_keyword = decision.get("keyword", "")
        normalized_keyword = normalize_keyword(raw_keyword)
        
        # 查找目標記憶（只找 agent 自己建的）
        target = db.find_memory_by_keyword(normalized_keyword, created_by="agent")
        
        if not target:
            # 找不到，轉為新建
            return self.remember_or_reinforce(decision)
        
        # 檢查內容差異
        new_content = decision.get("summary", "").strip()
        old_content = target.get("content", "").strip()
        similarity = _content_similarity(new_content, old_content)
        
        # 差異大 -> 視為衝突，標記待審核
        if similarity < 0.5:
            memory_id = db.insert_memory(
                tag=decision["tag"],
                content=new_content,
                category=decision["category"],
                importance=decision["importance"],
                keyword=normalized_keyword,
                raw_keyword=raw_keyword,
                expires_at=compute_expiry(decision["importance"]),
                created_by="agent",
                pending_review=True,
                conflict_with=target["id"]
            )
            # pending_review 的記憶不加入內存
            return {
                "memory_id": memory_id,
                "action_taken": "pending_review" if memory_id is not None else "skipped",
                "conflict_with": target["id"] if memory_id is not None else None,
                "skip_reason": "conflict_detected" if memory_id is not None else "insert_failed"
            }
        
        # 差異小 -> 直接更新
        new_importance = decision["importance"]
        new_expiry = compute_expiry(new_importance)
        ok = db.update_memory(target["id"], content=new_content,
                              importance=new_importance, expires_at=new_expiry)
        
        if ok:
            # 同步內存
            for m in self.memory_bank:
                if m.get("id") == target["id"]:
                    m["content"] = new_content
                    m["importance"] = new_importance
                    m["expires_at"] = new_expiry
                    break
        
        return {
            "memory_id": target["id"] if ok else None,
            "action_taken": "updated" if ok else "skipped",
            "conflict_with": None,
            "skip_reason": None if ok else "update_failed"
        }

    def archive_memory(self, decision):
        """
        Lin 判断"这件事已经失效/被推翻"：只能封存自己建立的记忆（created_by=agent），
        找不到符合条件的对象就什么都不做，绝不碰Anna手动建立的记忆。
        归档是逻辑删除（archived=True），不是物理删除，Anna仍可在数据库里找回。
        
        Phase 1: 加入 keyword normalization
        """
        from app.keyword_normalizer import normalize_keyword
        
        raw_keyword = decision.get("keyword", "")
        normalized_keyword = normalize_keyword(raw_keyword)
        
        target = db.find_memory_by_keyword(normalized_keyword, created_by="agent")
        if not target:
            return {
                "memory_id": None,
                "action_taken": "skipped",
                "conflict_with": None,
                "skip_reason": "not_found"
            }
        
        ok = db.archive_memory(target["id"])
        if ok:
            self.memory_bank = [m for m in self.memory_bank if m.get("id") != target["id"]]
        
        return {
            "memory_id": target["id"] if ok else None,
            "action_taken": "archived" if ok else "skipped",
            "conflict_with": None,
            "skip_reason": "db_error" if not ok else None
        }

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
                "created_by": r.get("created_by", "user"),
                "archived": r.get("archived", False),
                "time": _fmt_time(r.get("created_at")),
            }
            for r in db.load_memories()
        ]

    def recent_memory_text(self, n=8):
        """挑最重要的几条塞进 prompt（不是最新的几条——星级高的比刚存的更该被记住）。"""
        if not self.memory_bank:
            return ""
        active = [m for m in self.memory_bank if not m.get("archived")]
        top = sorted(active, key=lambda m: m.get("importance", 3), reverse=True)[:n]
        lines = "\n".join(f"[{m['category']}·{m['tag']}·{'⭐'*m.get('importance',3)}] {m['content']}" for m in top)
        return f"\n\n【Lin对Anna的记忆】\n{lines}"

    # ---------- 对话历史 ----------
    def add_conversation_turn(self, role, content, thinking=None, image_data=None, session_id=None, trace=None):
        """
        记录一轮对话：role 是 'anna' 或 'lin'，content 是说的话。
        用 deque(maxlen=config.CHAT_HISTORY_LIMIT) 自动保留最近N条，超过自动丢弃最旧的。
        同时写回 Supabase，让手机/电脑/网页三端下次打开能读到同一份记录。
        trace：Developer Panel 用的版本化 trace dict（TraceCollector.export()），可选，
        只有 lin 的回覆会带，不影响既有呼叫端（不传就是 None）。
        """
        print("[CHAT-ID-1]", id(self.conversation_history))
        target_session = session_id or self.current_session_id
        
        turn = {
            "role": role,
            "content": content,
            "thinking": thinking,
            "image_data": image_data,
            "time": datetime.now().isoformat(),
            "trace": trace,
        }
        self.conversation_history.append(turn)
        
        db.insert_conversation_turn(role, content, thinking=thinking, image_data=image_data, session_id=target_session, trace=trace)
        
        from app import session as session_module
        session_module.update_session_activity(target_session)
        
        if len(self.conversation_history) == 1 and role == "anna":
            title = content[:30] + "..." if len(content) > 30 else content
            session_module.update_session_title(target_session, title)

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

    # ---------- Body State (Phase 1) ----------
    def _load_body_state_snapshot(self):
        snapshot = db.load_state_value("body_state")
        if not isinstance(snapshot, dict):
            return

        def parse_dt(value):
            if not value:
                return None
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                # Existing tick/chat code uses naive datetimes.
                return parsed.replace(tzinfo=None)
            except (TypeError, ValueError):
                return None

        values = snapshot.get("body_values")
        if isinstance(values, dict):
            for key in ("tension", "heat", "sensitivity", "control"):
                try:
                    self.body_values[key] = max(0.0, min(100.0, float(values.get(key, self.body_values[key]))))
                except (TypeError, ValueError):
                    pass

        self.cycle_key = snapshot.get("cycle_key") or self.cycle_key
        self.cycle_started_at = parse_dt(snapshot.get("cycle_started_at"))
        self.cycle_expires_at = parse_dt(snapshot.get("cycle_expires_at"))
        self.last_tick_at = parse_dt(snapshot.get("last_tick_at"))
        self.active_event_key = snapshot.get("active_event_key")
        self.active_event_started_at = parse_dt(snapshot.get("active_event_started_at"))
        self.active_event_expires_at = parse_dt(snapshot.get("active_event_expires_at"))
        self.last_user_message_at = parse_dt(snapshot.get("last_user_message_at"))
        try:
            self.continuous_turns = int(snapshot.get("continuous_turns", 0))
        except (TypeError, ValueError):
            self.continuous_turns = 0

        restored_effects = []
        for raw in snapshot.get("active_after_effects", []):
            if not isinstance(raw, dict):
                continue
            try:
                from app.intimacy.after_effect import AfterEffect

                started = parse_dt(raw.get("started_at"))
                expires = parse_dt(raw.get("expires_at"))
                if not started or not expires:
                    continue
                restored_effects.append(AfterEffect(
                    source_event=str(raw.get("source_event", "")),
                    duration_minutes=int(raw.get("duration_minutes", 0)),
                    deltas_per_hour=dict(raw.get("deltas_per_hour") or {}),
                    description=str(raw.get("description", "")),
                    started_at=started,
                    expires_at=expires,
                ))
            except (TypeError, ValueError):
                continue
        self.active_after_effects = restored_effects

    def save_body_state(self):
        def iso(value):
            return value.isoformat() if value else None

        effects = []
        for effect in getattr(self, "active_after_effects", []) or []:
            effects.append({
                "source_event": effect.source_event,
                "duration_minutes": effect.duration_minutes,
                "deltas_per_hour": dict(effect.deltas_per_hour),
                "description": effect.description,
                "started_at": iso(effect.started_at),
                "expires_at": iso(effect.expires_at),
            })

        db.save_state_value("body_state", {
            "version": 1,
            "body_values": dict(self.body_values),
            "cycle_key": self.cycle_key,
            "cycle_started_at": iso(self.cycle_started_at),
            "cycle_expires_at": iso(self.cycle_expires_at),
            "last_tick_at": iso(self.last_tick_at),
            "active_event_key": self.active_event_key,
            "active_event_started_at": iso(self.active_event_started_at),
            "active_event_expires_at": iso(self.active_event_expires_at),
            "active_after_effects": effects,
            "last_user_message_at": iso(self.last_user_message_at),
            "continuous_turns": self.continuous_turns,
        })

    # ---------- 状态自评 ----------
    def update_mood(self, mood_dict):
        if not mood_dict:
            return
        self.mood = mood_dict
        print(f"[mood] 准备保存 mood_state: {self.mood!r}")
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
