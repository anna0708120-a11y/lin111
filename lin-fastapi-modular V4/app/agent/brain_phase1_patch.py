"""
Brain Phase 1 Patch - 記憶處理邏輯整合

這是 brain.py 中記憶處理部分的 Phase 1 版本。
提供一個函數替換原本的記憶處理邏輯，加入衝突檢查。

使用方式：
在 brain.py 的 generate_reply() 中，把原本的記憶處理邏輯：
    if decision:
        action = decision.get("action", "create")
        if action == "update":
            state.update_memory(decision)
        elif action == "archive":
            state.archive_memory(decision)
        else:
            state.remember_or_reinforce(decision)

替換成：
    if decision:
        from app.agent.brain_phase1_patch import handle_memory_decision_v2
        handle_memory_decision_v2(decision)
"""
from app.state import state
from app.state_phase1_patch import (
    remember_or_reinforce_v2,
    update_memory_v2,
    archive_memory_v2
)


def handle_memory_decision_v2(decision):
    """
    Phase 1 版本的記憶處理邏輯（帶衝突檢查）
    
    Args:
        decision: parse_memory_decision() 的回傳值
    
    Returns:
        dict: {
            "memory_id": int | None,
            "action_taken": str,
            "conflict_with": int | None,
            "pending_review": bool
        }
    """
    action = decision.get("action", "create")
    
    if action == "update":
        result = update_memory_v2(state, decision)
    elif action == "archive":
        result = archive_memory_v2(state, decision)
    else:  # create
        result = remember_or_reinforce_v2(state, decision)
    
    # 記錄到 activity_log（可選）
    if result.get("pending_review"):
        from app import db
        db.insert_log("memory_conflict", {
            "memory_id": result.get("memory_id"),
            "conflict_with": result.get("conflict_with"),
            "keyword": decision.get("keyword"),
            "summary": decision.get("summary")[:100]
        })
    
    return result


# 向後相容：提供一個 wrapper，行為跟原本的 state 方法一樣，但內部走 v2 邏輯
def migrate_to_v2():
    """
    把 state.remember_or_reinforce / update_memory / archive_memory 
    替換成 v2 版本（可選的遷移方式）
    
    使用方式（在 app 啟動時執行一次）：
        from app.agent.brain_phase1_patch import migrate_to_v2
        migrate_to_v2()
    
    之後所有對 state.remember_or_reinforce() 的調用都會自動走 v2 邏輯。
    """
    from app.state import state
    
    # 備份原本的方法
    state._remember_or_reinforce_v1 = state.remember_or_reinforce
    state._update_memory_v1 = state.update_memory
    state._archive_memory_v1 = state.archive_memory
    
    # 替換成 v2
    state.remember_or_reinforce = lambda decision: remember_or_reinforce_v2(state, decision)
    state.update_memory = lambda decision: update_memory_v2(state, decision)
    state.archive_memory = lambda decision: archive_memory_v2(state, decision)
    
    print("[brain_phase1_patch] Memory management migrated to v2 (conflict detection enabled)")


def rollback_to_v1():
    """回滾到 v1（測試用）"""
    from app.state import state
    
    if hasattr(state, '_remember_or_reinforce_v1'):
        state.remember_or_reinforce = state._remember_or_reinforce_v1
        state.update_memory = state._update_memory_v1
        state.archive_memory = state._archive_memory_v1
        print("[brain_phase1_patch] Rolled back to v1")
