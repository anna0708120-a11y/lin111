"""
Phase 1 DB Patch - 新增的資料庫函數

這些函數是 Phase 1 新增的，等測試穩定後會合併回 app/db.py
暫時獨立出來避免影響現有邏輯。
"""
from app import config

_client = None

if config.SUPABASE_URL and config.SUPABASE_KEY:
    try:
        from supabase import create_client
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    except Exception as e:
        print(f"[db_phase1_patch] Supabase 連接失敗: {e}")
        _client = None


# ---------- Phase 1: Conflict Detection ----------

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
        print(f"[db_phase1_patch] 查找衝突記憶失敗: {e}")
        return []


def insert_memory_with_conflict(tag, content, category="长期记忆", importance=3, 
                                  keyword="", raw_keyword="", expires_at=None, 
                                  created_by="user", pending_review=False, conflict_with=None):
    """
    插入記憶（Phase 1 版本，支援 conflict 欄位）
    
    Args:
        tag, content, category, importance, keyword, expires_at, created_by: 原有參數
        raw_keyword: 模型原始輸出的 keyword（未正規化）
        pending_review: 是否標記為待審核
        conflict_with: 衝突的舊記憶 id
    
    Returns:
        int | None: 成功回傳 id，失敗回傳 None
    """
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
                "raw_keyword": raw_keyword or keyword,
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
        print(f"[db_phase1_patch] 插入記憶失敗: {e}")
    return None


def load_pending_memories(limit=50):
    """
    讀取所有待審核的記憶（前端監控台用）
    
    Returns:
        List[dict]: 待審核記憶列表，包含完整欄位
    """
    if not _client:
        return []
    try:
        res = (
            _client.table("memory_bank")
            .select("id, tag, category, content, importance, keyword, raw_keyword, expires_at, created_at, created_by, pending_review, conflict_with, archived")
            .eq("pending_review", True)
            .eq("archived", False)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[db_phase1_patch] 讀取待審核記憶失敗: {e}")
        return []


def approve_memory(memory_id, archive_conflicts=True):
    """
    批准一條待審核記憶
    
    Args:
        memory_id: 要批准的記憶 id
        archive_conflicts: 是否同時歸檔衝突的舊記憶
    
    Returns:
        bool: 操作是否成功
    """
    if not _client or not memory_id:
        return False
    try:
        # 1. 取消 pending_review 標記
        _client.table("memory_bank").update({
            "pending_review": False
        }).eq("id", memory_id).execute()
        
        # 2. 如果需要歸檔衝突記憶
        if archive_conflicts:
            # 查出這條記憶的 conflict_with
            res = _client.table("memory_bank").select("conflict_with").eq("id", memory_id).execute()
            if res.data and res.data[0].get("conflict_with"):
                conflict_id = res.data[0]["conflict_with"]
                _client.table("memory_bank").update({"archived": True}).eq("id", conflict_id).execute()
        
        return True
    except Exception as e:
        print(f"[db_phase1_patch] 批准記憶失敗: {e}")
        return False


def reject_memory(memory_id):
    """
    拒絕一條待審核記憶（直接歸檔）
    
    Args:
        memory_id: 要拒絕的記憶 id
    
    Returns:
        bool: 操作是否成功
    """
    if not _client or not memory_id:
        return False
    try:
        _client.table("memory_bank").update({
            "archived": True,
            "pending_review": False
        }).eq("id", memory_id).execute()
        return True
    except Exception as e:
        print(f"[db_phase1_patch] 拒絕記憶失敗: {e}")
        return False


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
        print(f"[db_phase1_patch] 讀取記憶失敗: {e}")
        return []
