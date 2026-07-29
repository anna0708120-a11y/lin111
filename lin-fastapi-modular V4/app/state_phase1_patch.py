"""
State Phase 1 Patch - 記憶管理整合層

這是 state.py 的 Phase 1 擴展，提供：
1. 帶衝突檢查的記憶寫入
2. update/archive action 的 conflict-aware 版本
3. 待審核記憶的管理接口

使用方式：
- brain.py 可以選擇使用 state_phase1_patch 的函數
- 或繼續使用原有的 state.remember_or_reinforce()
- 兩者並存，逐步遷移
"""
from app.memory_conflict import handle_memory_with_conflict_check, detect_conflict
from app.keyword_normalizer import normalize_keyword
from app.db_phase1_patch import (
    find_conflicting_memories, 
    insert_memory_with_conflict,
    load_pending_memories,
    approve_memory,
    reject_memory
)
from app.memory_rules import compute_expiry
from app import db


def remember_or_reinforce_v2(state_obj, decision):
    """
    Phase 1 版本的 remember_or_reinforce，加入衝突檢查
    
    Args:
        state_obj: state.py 的 State 實例
        decision: parse_memory_decision() 的回傳值
    
    Returns:
        dict: {
            "memory_id": int | None,
            "action_taken": "created" | "reinforced" | "pending_review",
            "conflict_with": int | None,
            "pending_review": bool
        }
    """
    result = handle_memory_with_conflict_check(decision)
    
    # 同步到 state.memory_bank（內存快取）
    if result["memory_id"] and result["action_taken"] != "pending_review":
        # 正常建立或強化的記憶加入內存
        raw_keyword = decision.get("keyword", "")
        normalized_keyword = normalize_keyword(raw_keyword)
        
        if result["action_taken"] == "reinforced":
            # 更新內存中的記憶
            for m in state_obj.memory_bank:
                if m.get("id") == result["memory_id"]:
                    m["importance"] = decision["importance"]
                    m["expires_at"] = compute_expiry(decision["importance"])
                    break
        else:
            # 新建記憶加入內存
            state_obj.memory_bank.append({
                "id": result["memory_id"],
                "tag": decision["tag"],
                "category": decision["category"],
                "content": decision["summary"],
                "importance": decision["importance"],
                "keyword": normalized_keyword,
                "expires_at": compute_expiry(decision["importance"]),
                "created_by": "agent",
            })
            if len(state_obj.memory_bank) > 300:
                state_obj.memory_bank.pop(0)
    
    return {
        "memory_id": result["memory_id"],
        "action_taken": result["action_taken"],
        "conflict_with": result["conflict_with"],
        "pending_review": (result["action_taken"] == "pending_review")
    }


def update_memory_v2(state_obj, decision):
    """
    Phase 1 版本的 update_memory，加入衝突檢查
    
    Lin 判斷「同一件事已經變化」，但新內容可能跟舊內容差很多：
    - 如果差異大 -> 標記 pending_review
    - 如果差異小 -> 直接更新
    
    Args:
        state_obj: state.py 的 State 實例
        decision: parse_memory_decision() 的回傳值
    
    Returns:
        dict: 同 remember_or_reinforce_v2
    """
    raw_keyword = decision.get("keyword", "")
    normalized_keyword = normalize_keyword(raw_keyword)
    
    # 1. 查找目標記憶（只找 agent 自己建的）
    target = db.find_memory_by_keyword(normalized_keyword, created_by="agent")
    
    if not target:
        # 找不到，轉為新建（這跟原本邏輯一樣）
        return remember_or_reinforce_v2(state_obj, decision)
    
    # 2. 檢查內容差異
    from app.memory_conflict import _content_similarity
    new_content = decision.get("summary", "").strip()
    old_content = target.get("content", "").strip()
    similarity = _content_similarity(new_content, old_content)
    
    # 3. 差異大 -> 視為衝突，標記待審核
    if similarity < 0.5:
        memory_id = insert_memory_with_conflict(
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
        return {
            "memory_id": memory_id,
            "action_taken": "pending_review",
            "conflict_with": target["id"],
            "pending_review": True
        }
    
    # 4. 差異小 -> 直接更新
    new_importance = decision["importance"]
    new_expiry = compute_expiry(new_importance)
    ok = db.update_memory(target["id"], content=new_content,
                          importance=new_importance, expires_at=new_expiry)
    
    if ok:
        # 同步內存
        for m in state_obj.memory_bank:
            if m.get("id") == target["id"]:
                m["content"] = new_content
                m["importance"] = new_importance
                m["expires_at"] = new_expiry
                break
    
    return {
        "memory_id": target["id"],
        "action_taken": "updated",
        "conflict_with": None,
        "pending_review": False
    }


def archive_memory_v2(state_obj, decision):
    """
    Phase 1 版本的 archive_memory，邏輯不變（archive 不需要衝突檢查）
    
    這個函數主要是為了保持接口一致性，實際邏輯跟原本一樣。
    """
    raw_keyword = decision.get("keyword", "")
    normalized_keyword = normalize_keyword(raw_keyword)
    
    target = db.find_memory_by_keyword(normalized_keyword, created_by="agent")
    if not target:
        return {
            "memory_id": None,
            "action_taken": "not_found",
            "conflict_with": None,
            "pending_review": False
        }
    
    ok = db.archive_memory(target["id"])
    if ok:
        state_obj.memory_bank = [m for m in state_obj.memory_bank if m.get("id") != target["id"]]
    
    return {
        "memory_id": target["id"] if ok else None,
        "action_taken": "archived" if ok else "failed",
        "conflict_with": None,
        "pending_review": False
    }


def get_pending_memories():
    """
    取得所有待審核的記憶（前端監控台用）
    
    Returns:
        List[dict]: 待審核記憶列表
    """
    return load_pending_memories()


def approve_pending_memory(memory_id, archive_old=True):
    """
    批准一條待審核記憶
    
    Args:
        memory_id: 要批准的記憶 id
        archive_old: 是否同時歸檔衝突的舊記憶（預設 True）
    
    Returns:
        bool: 操作是否成功
    """
    return approve_memory(memory_id, archive_conflicts=archive_old)


def reject_pending_memory(memory_id):
    """
    拒絕一條待審核記憶（直接歸檔）
    
    Args:
        memory_id: 要拒絕的記憶 id
    
    Returns:
        bool: 操作是否成功
    """
    return reject_memory(memory_id)
