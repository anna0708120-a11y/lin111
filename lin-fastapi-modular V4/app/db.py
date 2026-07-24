"""
跟 Supabase 之间的读写，全部收在这个文件。

state.py 透过这个模块存取数据，不直接碰 Supabase。
如果没填 SUPABASE_URL / SUPABASE_KEY，这里每个函数都安静地什么都不做、
返回空结果，整个 app 会自动退回纯内存模式，不会因为没接 Supabase 就跑不起来
——这也是为什么可以先部署、之后才补 Supabase，中间不会中断。
"""
from app import config

_client = None

if config.SUPABASE_URL and config.SUPABASE_KEY:
    try:
        from supabase import create_client
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        print("[db] Supabase 已连接")
    except Exception as e:
        print(f"[db] Supabase 连接失败，退回内存模式: {e}")
        _client = None


def is_connected():
    return _client is not None


# ---------- 通用状态 (key -> value，比如 last_anchor_at、proactive设置) ----------
def load_state_value(key, default=None):
    if not _client:
        return default
    try:
        res = _client.table("app_state").select("value").eq("key", key).execute()
        if res.data:
            return res.data[0]["value"]
    except Exception as e:
        print(f"[db] 读取 {key} 失败: {e}")
    return default


def save_state_value(key, value):
    if not _client:
        return
    try:
        _client.table("app_state").upsert({"key": key, "value": value}).execute()
    except Exception as e:
        print(f"[db] 写入 {key} 失败: {e}")


def delete_state_value(key):
    if not _client:
        return
    try:
        _client.table("app_state").delete().eq("key", key).execute()
    except Exception as e:
        print(f"[db] 删除 {key} 失败: {e}")


# ---------- 长期记忆 ----------
def load_memories(limit=200):
    if not _client:
        return []
    try:
        res = (
            _client.table("memory_bank")
            .select("id, tag, category, content, importance, keyword, expires_at, created_at")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[db] 读取记忆失败: {e}")
        return []


def insert_memory(tag, content, category="长期记忆", importance=3, keyword="", expires_at=None):
    """插入一条记忆，成功的话回传 Supabase 分配的 id（前端删除要用），失败回传 None。"""
    if not _client:
        return None
    try:
        res = (
            _client.table("memory_bank")
            .insert({
                "tag": tag,
                "content": content,
                "category": category,
                "importance": importance,
                "keyword": keyword,
                "expires_at": expires_at,
            })
            .execute()
        )
        if res.data:
            return res.data[0].get("id")
    except Exception as e:
        print(f"[db] 写入记忆失败: {e}")
    return None


def find_memory_by_keyword(keyword):
    """找同一件事有没有已经存过（用关键字精确比对，还没有语意搜索）。"""
    if not _client or not keyword:
        return None
    try:
        res = (
            _client.table("memory_bank")
            .select("id, importance, content")
            .eq("keyword", keyword)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] 比对记忆失败: {e}")
        return None


def reinforce_memory(memory_id, importance, expires_at):
    """同一件事又被提到：星级调高、到期时间重算。"""
    if not _client:
        return
    try:
        _client.table("memory_bank").update({
            "importance": importance,
            "expires_at": expires_at,
        }).eq("id", memory_id).execute()
    except Exception as e:
        print(f"[db] 更新记忆失败: {e}")


def delete_memory(memory_id):
    if not _client:
        return
    try:
        _client.table("memory_bank").delete().eq("id", memory_id).execute()
    except Exception as e:
        print(f"[db] 删除记忆失败: {e}")


def delete_expired_memories(now_iso):
    """每周整理用：把到期的记忆删掉，回传删了几条。"""
    if not _client:
        return 0
    try:
        res = (
            _client.table("memory_bank")
            .delete()
            .lt("expires_at", now_iso)
            .execute()
        )
        return len(res.data or [])
    except Exception as e:
        print(f"[db] 清理到期记忆失败: {e}")
        return 0


# ---------- 监控日志 ----------
def load_logs(limit=100):
    if not _client:
        return []
    try:
        res = (
            _client.table("activity_log")
            .select("event_type, content, created_at")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[db] 读取监控日志失败: {e}")
        return []


def insert_log(event_type, content):
    if not _client:
        return
    try:
        _client.table("activity_log").insert({"event_type": event_type, "content": content}).execute()
    except Exception as e:
        print(f"[db] 写入监控日志失败: {e}")


# ---------- 对话历史（跨装置同步：手机 dock / 电脑 dock / 网页版 共用一份） ----------
def load_conversations(limit=500):
    """启动时读一份最近的聊天记录进内存，让三端打开时看到同一份对话。"""
    if not _client:
        return []
    try:
        res = (
            _client.table("conversation_history")
            .select("role, content, thinking, image_data, created_at")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = res.data or []
        rows.reverse()  # 转回时间正序（旧->新），跟内存 deque 的顺序一致
        return rows
    except Exception as e:
        print(f"[db] 读取对话历史失败: {e}")
        return []

def insert_conversation_turn(role, content, thinking=None, image_data=None):
    if not _client:
        return
    try:
        _client.table("conversation_history").insert({
            "role": role,
            "content": content,
            "thinking": thinking,
            "image_data": image_data,
        }).execute()
    except Exception as e:
        print(f"[db] 写入对话历史失败: {e}")

# ---------- Lin 的碎碎念 ----------
def load_notes(limit=50):
    if not _client:
        return []
    try:
        res = (
            _client.table("chen_notes")
            .select("content, created_at")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[db] 读取碎碎念失败: {e}")
        return []


def insert_note(content):
    if not _client:
        return
    try:
        _client.table("chen_notes").insert({"content": content}).execute()
    except Exception as e:
        print(f"[db] 写入碎碎念失败: {e}")
# ---------- Context State（Mac/天气/日历/屏幕时间/定位 快照） ----------
def load_context(source):
    """读某个来源最新的一条快照。找不到回传 None。"""
    if not _client:
        return None
    try:
        res = (
            _client.table("context_state")
            .select("payload, updated_at")
            .eq("source", source)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] 读取 context {source} 失败: {e}")
        return None


def save_context(source, payload):
    """写入/更新某个来源的最新快照（同一个source只留一条,用upsert）。"""
    if not _client:
        return
    try:
        from datetime import datetime, timezone
        _client.table("context_state").upsert({
            "source": source,
            "payload": payload,
            # 之前这里写的是字符串 "now()"（带括号），Postgres会解析失败导致upsert静默失败，
            # 天气/Mac状态永远存不进数据库、自己却看不出来。改成Python自己算好时间再传过去。
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        print(f"[db] 写入 context {source} 失败: {e}")
        
# ---------- Photos（图片资料卡，图片本体在 Supabase Storage） ----------
def insert_photo(filename, url, caption=""):
    if not _client:
        return None
    try:
        res = (
            _client.table("photos")
            .insert({"filename": filename, "url": url, "caption": caption})
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] 写入图片记录失败: {e}")
        return None

def load_recent_photos(limit=12):
    if not _client:
        return []
    try:
        res = (
            _client.table("photos")
            .select("id, filename, url, caption, created_at")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[db] 读取图片列表失败: {e}")
        return []

def upload_photo_file(local_path, storage_filename):
    """把本地文件上传到 Supabase Storage，回传公开访问网址；失败回 None。"""
    if not _client:
        return None
    try:
        from app import config
        with open(local_path, "rb") as f:
            _client.storage.from_(config.PHOTO_BUCKET).upload(
                storage_filename, f, {"content-type": "image/jpeg"}
            )
        return _client.storage.from_(config.PHOTO_BUCKET).get_public_url(storage_filename)
    except Exception as e:
        print(f"[db] 上传图片文件失败: {e}")
        return None

