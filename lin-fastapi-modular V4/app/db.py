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
            .select("id, tag, category, content, importance, keyword, expires_at, created_at, created_by, archived")
            .eq("archived", False)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[db] 读取记忆失败: {e}")
        return []


def insert_memory(tag, content, category="长期记忆", importance=3, keyword="", expires_at=None,
                   created_by="user", raw_keyword="", pending_review=False, conflict_with=None):
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
                "raw_keyword": raw_keyword,
                "expires_at": expires_at,
                "created_by": created_by,
                "pending_review": pending_review,
                "conflict_with": conflict_with,
            })
            .execute()
        )
        if res.data:
            return res.data[0].get("id")
    except Exception as e:
        print(f"[db] 写入记忆失败: {e}")
    return None


def find_memory_by_keyword(keyword, created_by=None):
    """
    找同一件事有没有已经存过（用关键字精确比对，还没有语意搜索）。
    created_by=None：不限制来源，给 reinforce 用（现有逻辑不变）。
    created_by="agent"：只找 Lin 自己建立的记忆，给 update/archive 用——
      同一 keyword 如果命中的是 Anna 手动建的（created_by="user"），
      这里会回传 None，调用端就不会去动那条记忆。
    """
    if not _client or not keyword:
        return None
    try:
        query = (
            _client.table("memory_bank")
            .select("id, importance, content, created_by")
            .eq("keyword", keyword)
            .eq("archived", False)
        )
        if created_by is not None:
            query = query.eq("created_by", created_by)
        res = query.limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] 比对记忆失败: {e}")
        return None


def update_memory(memory_id, content=None, importance=None, expires_at=None):
    """更新一条已存在的记忆（修正用），只更新有给值的字段。"""
    if not _client or not memory_id:
        return False
    patch = {}
    if content is not None:
        patch["content"] = content
    if importance is not None:
        patch["importance"] = importance
    if expires_at is not None:
        patch["expires_at"] = expires_at
    if not patch:
        return False
    try:
        _client.table("memory_bank").update(patch).eq("id", memory_id).execute()
        return True
    except Exception as e:
        print(f"[db] 更新记忆失败: {e}")
        return False


def archive_memory(memory_id):
    """把记忆标记为已归档（逻辑删除，不物理删除），用于处理过期或被推翻的记忆。"""
    if not _client or not memory_id:
        return False
    try:
        _client.table("memory_bank").update({"archived": True}).eq("id", memory_id).execute()
        return True
    except Exception as e:
        print(f"[db] 归档记忆失败: {e}")
        return False


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
    """每周整理用：把到期的记忆归档（软删除，不物理删除），回传归档了几条。"""
    if not _client:
        return 0
    try:
        res = (
            _client.table("memory_bank")
            .update({"archived": True})
            .lt("expires_at", now_iso)
            .eq("archived", False)
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
def load_conversations(limit=500, session_id=None):
    """启动时读一份最近的聊天记录进内存，让三端打开时看到同一份对话。
    
    Args:
        limit: 最多读取多少条
        session_id: 如果指定，只读取该 session 的对话；否则读取所有对话（向后兼容）
    """
    if not _client:
        return []
    try:
        query = _client.table("conversation_history").select("id, role, content, thinking, image_data, created_at, session_id, trace")
        
        if session_id:
            query = query.eq("session_id", session_id)
        
        res = query.order("created_at", desc=True).limit(limit).execute()
        
        rows = res.data or []
        rows.reverse()  # 转回时间正序（旧->新），跟内存 deque 的顺序一致
        return rows
    except Exception as e:
        import traceback
        print(f"[db] 读取对话历史失败: {e}")
        traceback.print_exc()
        return []

def insert_conversation_turn(role, content, thinking=None, image_data=None, session_id=None, trace=None):
    if not _client:
        return
    try:
        _client.table("conversation_history").insert({
            "role": role,
            "content": content,
            "thinking": thinking,
            "image_data": image_data,
            "session_id": session_id,
            "trace": trace,
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


# ---------- Phase 1: Conflict Detection & Memory Review ----------
def find_conflicting_memories(keyword, created_by=None):
    """
    尋找可能衝突的記憶（同 keyword 的所有未歸檔記憶）
    
    Args:
        keyword: 正規化後的關鍵字
        created_by: 過濾來源 ("agent" / "user" / None=不限)
    
    Returns:
        List[dict]: 所有符合條件的記憶，按 created_at 排序（舊→新）
    """
    if not _client or not keyword:
        return []
    try:
        query = (
            _client.table("memory_bank")
            .select("id, importance, content, created_by, created_at, keyword, raw_keyword, pending_review, conflict_with")
            .eq("keyword", keyword)
            .eq("archived", False)
        )
        if created_by is not None:
            query = query.eq("created_by", created_by)
        res = query.order("created_at", desc=False).execute()
        return res.data or []
    except Exception as e:
        print(f"[db] 查找衝突記憶失敗: {e}")
        return []


def load_memories_with_conflicts(limit=200):
    """
    讀取記憶（包含 Phase 1 新增欄位）
    
    Returns:
        List[dict]: 記憶列表，包含 raw_keyword, pending_review, conflict_with
    """
    if not _client:
        return []
    try:
        res = (
            _client.table("memory_bank")
            .select("id, tag, category, content, importance, keyword, raw_keyword, expires_at, created_at, created_by, archived, pending_review, conflict_with")
            .eq("archived", False)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[db] 讀取記憶失敗: {e}")
        return []

# ---------- Phase 2: Memory Trace ----------
def insert_memory_trace(trace):
    """
    插入一條 memory trace 記錄
    
    Args:
        trace: MemoryTrace 物件
    """
    if not _client:
        return
    try:
        import json
        from datetime import datetime
        
        # 準備資料
        data = {
            "session_id": trace.session_id,
            "message_id": trace.message_id,
            "created_at": trace.created_at.isoformat() if trace.created_at else datetime.now().isoformat(),
            "reasoning_text": trace.reasoning_text,
            "raw_decision_block": trace.raw_decision_block,
            "parse_success": trace.parse_success,
            "parsed_decision": json.dumps(trace.parsed_decision) if trace.parsed_decision else None,
            "parse_error": trace.parse_error,
            "backend_action": trace.backend_action,
            "action_taken": trace.action_taken,
            "skip_reason": trace.skip_reason,
            "conflict_with": trace.conflict_with,
            "memory_id": trace.memory_id,
            "db_success": trace.db_success,
            "db_error": trace.db_error,
        }
        
        _client.table("memory_traces").insert(data).execute()
    except Exception as e:
        print(f"[db] 插入 memory trace 失敗: {e}")


def load_memory_traces(limit=50, session_id=None, action_taken=None):
    """
    讀取 memory traces
    
    Args:
        limit: 最多讀取幾條
        session_id: 過濾特定 session
        action_taken: 過濾特定 action (created/reinforced/skipped/...)
    
    Returns:
        List[dict]: trace 列表
    """
    if not _client:
        return []
    try:
        query = _client.table("memory_traces").select("*")
        
        if session_id:
            query = query.eq("session_id", session_id)
        if action_taken:
            query = query.eq("action_taken", action_taken)
        
        res = query.order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        print(f"[db] 讀取 memory traces 失敗: {e}")
        return []


def get_memory_trace_stats(days=7):
    """
    取得 memory trace 統計數據
    
    Args:
        days: 統計最近 N 天
    
    Returns:
        dict: 統計數據
    """
    if not _client:
        return {}
    
    try:
        from datetime import datetime, timedelta
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        # 總數
        total_res = _client.table("memory_traces").select("id", count="exact").gte("created_at", since).execute()
        total_count = total_res.count if hasattr(total_res, 'count') else 0
        
        # 成功數（parse_success=true AND db_success=true AND action_taken != 'skipped'）
        success_res = _client.table("memory_traces").select("id", count="exact")\
            .gte("created_at", since)\
            .eq("parse_success", True)\
            .eq("db_success", True)\
            .neq("action_taken", "skipped")\
            .execute()
        success_count = success_res.count if hasattr(success_res, 'count') else 0
        
        # Parse 失敗數
        parse_fail_res = _client.table("memory_traces").select("id", count="exact")\
            .gte("created_at", since)\
            .eq("parse_success", False)\
            .execute()
        parse_fail_count = parse_fail_res.count if hasattr(parse_fail_res, 'count') else 0
        
        # Skip 原因分布（取前 10）
        skip_reasons = _client.table("memory_traces").select("skip_reason")\
            .gte("created_at", since)\
            .not_.is_("skip_reason", "null")\
            .execute()
        
        # 統計 skip_reason 分布
        skip_distribution = {}
        for row in (skip_reasons.data or []):
            reason = row.get("skip_reason", "unknown")
            skip_distribution[reason] = skip_distribution.get(reason, 0) + 1
        
        return {
            "total_count": total_count,
            "success_count": success_count,
            "parse_fail_count": parse_fail_count,
            "success_rate": round(success_count / total_count * 100, 2) if total_count > 0 else 0,
            "skip_distribution": skip_distribution,
            "days": days,
        }
    except Exception as e:
        print(f"[db] 取得 memory trace 統計失敗: {e}")
        return {}
