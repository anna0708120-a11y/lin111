"""
Memory Review API - Phase 1

提供前端監控台管理待審核記憶的接口。

Endpoints:
- GET  /api/memory/pending      - 取得所有待審核記憶
- POST /api/memory/approve/:id  - 批准一條記憶
- POST /api/memory/reject/:id   - 拒絕一條記憶
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.state_phase1_patch import (
    get_pending_memories,
    approve_pending_memory,
    reject_pending_memory
)

router = APIRouter(prefix="/api/memory", tags=["memory_review"])


class ApproveRequest(BaseModel):
    archive_old: bool = True  # 是否同時歸檔衝突的舊記憶


@router.get("/pending")
async def list_pending_memories():
    """
    取得所有待審核的記憶
    
    回傳格式：
    {
      "pending_memories": [
        {
          "id": 123,
          "tag": "Anna 喜歡的食物",
          "content": "Anna 現在最愛吃朱古力",
          "keyword": "chocolate",
          "raw_keyword": "朱古力",
          "importance": 4,
          "conflict_with": 120,
          "created_at": "2024-01-15T10:30:00Z",
          "conflicting_memory": {
            "id": 120,
            "content": "Anna 不喜歡吃朱古力",
            "created_at": "2024-01-10T08:00:00Z"
          }
        }
      ],
      "total": 1
    }
    """
    try:
        pending = get_pending_memories()
        
        # 補充衝突記憶的內容（方便前端顯示對比）
        from app import db
        for mem in pending:
            conflict_id = mem.get("conflict_with")
            if conflict_id:
                # 查詢衝突的舊記憶
                conflicts = db.find_memory_by_keyword(mem.get("keyword"), created_by="agent")
                for c in conflicts:
                    if c["id"] == conflict_id:
                        mem["conflicting_memory"] = {
                            "id": c["id"],
                            "content": c["content"],
                            "created_at": c.get("created_at"),
                            "importance": c.get("importance")
                        }
                        break
        
        return {
            "pending_memories": pending,
            "total": len(pending)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得待審核記憶失敗: {str(e)}")


@router.post("/approve/{memory_id}")
async def approve_memory_endpoint(memory_id: int, req: Optional[ApproveRequest] = None):
    """
    批准一條待審核記憶
    
    Args:
        memory_id: 要批准的記憶 id
        archive_old: 是否同時歸檔衝突的舊記憶（預設 True）
    
    回傳：
    {
      "success": true,
      "message": "記憶已批准",
      "memory_id": 123
    }
    """
    try:
        archive_old = req.archive_old if req else True
        success = approve_pending_memory(memory_id, archive_old=archive_old)
        
        if not success:
            raise HTTPException(status_code=404, detail="記憶不存在或操作失敗")
        
        # 同步到內存（重新載入）
        from app.state import state
        state.reload_memories()
        
        return {
            "success": True,
            "message": "記憶已批准" + ("，舊記憶已歸檔" if archive_old else ""),
            "memory_id": memory_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批准記憶失敗: {str(e)}")


@router.post("/reject/{memory_id}")
async def reject_memory_endpoint(memory_id: int):
    """
    拒絕一條待審核記憶（直接歸檔）
    
    回傳：
    {
      "success": true,
      "message": "記憶已拒絕",
      "memory_id": 123
    }
    """
    try:
        success = reject_pending_memory(memory_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="記憶不存在或操作失敗")
        
        return {
            "success": True,
            "message": "記憶已拒絕並歸檔",
            "memory_id": memory_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"拒絕記憶失敗: {str(e)}")


@router.get("/conflicts/summary")
async def get_conflicts_summary():
    """
    取得衝突統計摘要（監控台用）
    
    回傳：
    {
      "pending_count": 3,
      "recent_conflicts": [
        {
          "keyword": "chocolate",
          "count": 2,
          "latest_at": "2024-01-15T10:30:00Z"
        }
      ]
    }
    """
    try:
        pending = get_pending_memories()
        
        # 統計各 keyword 的衝突次數
        keyword_counts = {}
        for mem in pending:
            kw = mem.get("keyword", "unknown")
            if kw not in keyword_counts:
                keyword_counts[kw] = {
                    "keyword": kw,
                    "count": 0,
                    "latest_at": mem.get("created_at")
                }
            keyword_counts[kw]["count"] += 1
            # 更新最新時間
            if mem.get("created_at") > keyword_counts[kw]["latest_at"]:
                keyword_counts[kw]["latest_at"] = mem.get("created_at")
        
        recent_conflicts = sorted(
            keyword_counts.values(),
            key=lambda x: x["latest_at"],
            reverse=True
        )[:10]
        
        return {
            "pending_count": len(pending),
            "recent_conflicts": recent_conflicts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得統計失敗: {str(e)}")
