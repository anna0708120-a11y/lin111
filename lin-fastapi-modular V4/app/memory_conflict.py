"""
Memory Conflict Detection - Phase 1

衝突偵測邏輯：
1. 檢查同 keyword 是否已有記憶
2. 判斷是「強化」還是「衝突」
3. 衝突時標記 pending_review，等 Anna 審核

直接依賴 app.db（而非獨立的 patch 模組），避免維護兩套邏輯。
"""
from app import db
from app.keyword_normalizer import normalize_keyword
from app.memory_rules import compute_expiry


def _content_similarity(text1, text2):
    """
    簡單的內容相似度計算（Phase 1 用字符重疊率）
    Phase 2 可改用 embedding cosine similarity
    
    Returns:
        float: 0.0 ~ 1.0
    """
    if not text1 or not text2:
        return 0.0
    
    # 轉成字符集合，計算 Jaccard 相似度
    set1 = set(text1.lower())
    set2 = set(text2.lower())
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    if union == 0:
        return 0.0
    
    return intersection / union


def detect_conflict(decision):
    """
    偵測記憶衝突
    
    Args:
        decision: parse_memory_decision() 的回傳值
        
    Returns:
        dict: {
            "has_conflict": bool,
            "conflicting_memory": dict | None,
            "action": "create" | "reinforce" | "conflict"
        }
    """
    raw_keyword = decision.get("keyword", "").strip()
    if not raw_keyword:
        return {"has_conflict": False, "conflicting_memory": None, "action": "create"}
    
    # 1. 正規化 keyword
    normalized_keyword = normalize_keyword(raw_keyword)
    
    # 2. 查找同 keyword 的記憶（只找 agent 自己建立的）
    conflicts = db.find_conflicting_memories(normalized_keyword, created_by="agent")
    
    if not conflicts:
        return {"has_conflict": False, "conflicting_memory": None, "action": "create"}
    
    # 3. 取最新的一條作為衝突對象
    existing = conflicts[-1]
    
    # 4. 判斷是「強化」還是「衝突」
    new_content = decision.get("summary", "").strip()
    old_content = existing.get("content", "").strip()
    
    # 簡單規則：內容相似度 > 70% 視為強化，否則視為衝突
    if _content_similarity(new_content, old_content) > 0.7:
        return {
            "has_conflict": False,
            "conflicting_memory": existing,
            "action": "reinforce"
        }
    
    # 5. 確認為衝突
    return {
        "has_conflict": True,
        "conflicting_memory": existing,
        "action": "conflict"
    }


def handle_memory_with_conflict_check(decision):
    """Write a memory while preserving the existing conflict-review path."""
    conflict_result = detect_conflict(decision)
    raw_keyword = decision.get("keyword", "").strip()
    normalized_keyword = normalize_keyword(raw_keyword)

    def failed(reason):
        return {
            "success": False,
            "memory_id": None,
            "action_taken": "skipped",
            "conflict_with": None,
            "skip_reason": reason,
            "error_reason": reason,
        }

    def mark_pending_review(existing):
        memory_result = db.insert_memory(
            tag=decision["tag"],
            content=decision["summary"],
            category=decision["category"],
            importance=decision["importance"],
            keyword=normalized_keyword,
            raw_keyword=raw_keyword,
            expires_at=compute_expiry(decision["importance"]),
            created_by="agent",
            pending_review=True,
            conflict_with=existing["id"],
        )
        memory_id = memory_result.get("memory_id") if memory_result.get("success") else None
        return {
            "success": memory_result["success"],
            "memory_id": memory_id,
            "action_taken": "pending_review" if memory_id is not None else "skipped",
            "conflict_with": existing["id"] if memory_id is not None else None,
            "skip_reason": None if memory_id is not None else memory_result["error_reason"],
            "error_reason": memory_result["error_reason"],
        }

    # Lifecycle actions must operate on the Retrieval candidate the model received.
    # The backend still verifies that it is an active agent-created memory.
    lifecycle_action = decision.get("action")
    if lifecycle_action in ("reinforce", "conflict"):
        target_id = decision.get("memory_id")
        existing = db.find_memory_by_id(target_id, created_by="agent") if target_id else None
        if not existing:
            return failed("lifecycle_target_not_found")
        if lifecycle_action == "reinforce":
            new_importance = max(existing.get("importance", 3), decision["importance"])
            new_expiry = compute_expiry(new_importance)
            if not db.reinforce_memory(existing["id"], new_importance, new_expiry):
                return failed("reinforce_failed")
            return {
                "success": True,
                "memory_id": existing["id"],
                "action_taken": "reinforced",
                "conflict_with": None,
                "skip_reason": None,
                "error_reason": None,
            }
        return mark_pending_review(existing)

    if conflict_result["action"] == "reinforce":
        existing = conflict_result["conflicting_memory"]
        new_importance = max(existing.get("importance", 3), decision["importance"])
        new_expiry = compute_expiry(new_importance)
        if not db.reinforce_memory(existing["id"], new_importance, new_expiry):
            return failed("reinforce_failed")
        return {
            "success": True,
            "memory_id": existing["id"],
            "action_taken": "reinforced",
            "conflict_with": None,
            "skip_reason": None,
            "error_reason": None,
        }

    if conflict_result["action"] == "conflict":
        return mark_pending_review(conflict_result["conflicting_memory"])

    memory_result = db.insert_memory(
        tag=decision["tag"],
        content=decision["summary"],
        category=decision["category"],
        importance=decision["importance"],
        keyword=normalized_keyword,
        raw_keyword=raw_keyword,
        expires_at=compute_expiry(decision["importance"]),
        created_by="agent",
        pending_review=False,
        conflict_with=None,
    )
    memory_id = memory_result.get("memory_id") if memory_result.get("success") else None
    return {
        "success": memory_result["success"],
        "memory_id": memory_id,
        "action_taken": "created" if memory_id is not None else "skipped",
        "conflict_with": None,
        "skip_reason": None if memory_id is not None else memory_result["error_reason"],
        "error_reason": memory_result["error_reason"],
    }
