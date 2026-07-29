"""
Memory Trace - Phase 2

記錄每次 Memory 決策的完整執行鏈路，提供可觀測性。

Decision → Parser → Backend → DB
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import json

# Skip Reason 枚舉
SKIP_REASONS = {
    "worth_no": "模型判斷不值得記",
    "parse_failed": "解析 [MEMORY_DECISION] 失敗",
    "already_exists": "keyword 已存在且內容相似（reinforce）",
    "conflict_detected": "衝突待審核",
    "permission_denied": "試圖修改 user 建立的記憶",
    "db_error": "資料庫操作失敗",
}


@dataclass
class MemoryTrace:
    """Memory 決策的完整 trace"""
    
    # 會話資訊
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    created_at: Optional[datetime] = None
    
    # Step 1: 模型輸出
    reasoning_text: Optional[str] = None
    raw_decision_block: Optional[str] = None
    
    # Step 2: Parser
    parse_success: bool = False
    parsed_decision: Optional[dict] = None
    parse_error: Optional[str] = None
    
    # Step 3: Backend
    backend_action: Optional[str] = None  # remember_or_reinforce / update_memory / archive_memory
    action_taken: Optional[str] = None    # created / reinforced / pending_review / skipped / updated / archived
    skip_reason: Optional[str] = None
    conflict_with: Optional[int] = None
    
    # Step 4: DB
    memory_id: Optional[int] = None
    db_success: bool = True
    db_error: Optional[str] = None
    
    def to_dict(self):
        """轉換為 dict（用於 JSON 序列化）"""
        data = asdict(self)
        # datetime 轉 ISO string
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        return data
    
    def is_successful(self):
        """判斷這次決策是否成功執行"""
        return (
            self.parse_success and 
            self.db_success and 
            self.action_taken not in ['skipped', None]
        )
    
    def get_skip_reason_desc(self):
        """取得 skip_reason 的中文說明"""
        if not self.skip_reason:
            return None
        return SKIP_REASONS.get(self.skip_reason, self.skip_reason)


# 全局 trace 收集器（當前會話的 trace，在 brain.py 中初始化）
_current_trace: Optional[MemoryTrace] = None


def start_trace(session_id: str = None, message_id: str = None) -> MemoryTrace:
    """開始一個新的 trace"""
    global _current_trace
    _current_trace = MemoryTrace(
        session_id=session_id,
        message_id=message_id,
        created_at=datetime.now()
    )
    return _current_trace


def get_current_trace() -> Optional[MemoryTrace]:
    """取得當前的 trace"""
    return _current_trace


def clear_trace():
    """清除當前 trace"""
    global _current_trace
    _current_trace = None


def record_model_output(reasoning_text: str, raw_decision_block: str = None):
    """記錄模型輸出（Step 1）"""
    if _current_trace:
        _current_trace.reasoning_text = reasoning_text
        _current_trace.raw_decision_block = raw_decision_block


def record_parse_result(success: bool, parsed_decision: dict = None, error: str = None):
    """記錄 Parser 結果（Step 2）"""
    if _current_trace:
        _current_trace.parse_success = success
        _current_trace.parsed_decision = parsed_decision
        _current_trace.parse_error = error
        
        # 如果 parse 失敗，設定 skip_reason
        if not success:
            _current_trace.action_taken = "skipped"
            _current_trace.skip_reason = "parse_failed"


def record_backend_action(action: str, result: dict):
    """
    記錄 Backend 執行結果（Step 3）
    
    Args:
        action: remember_or_reinforce / update_memory / archive_memory
        result: backend 函數回傳的 dict，包含：
            - memory_id
            - action_taken: created / reinforced / pending_review / ...
            - conflict_with (optional)
    """
    if _current_trace:
        _current_trace.backend_action = action
        _current_trace.memory_id = result.get("memory_id")
        _current_trace.action_taken = result.get("action_taken")
        _current_trace.conflict_with = result.get("conflict_with")
        
        # 判斷是否為 skip 情況
        if result.get("action_taken") == "skipped":
            _current_trace.skip_reason = result.get("skip_reason", "unknown")
        elif result.get("action_taken") == "pending_review":
            _current_trace.skip_reason = "conflict_detected"


def record_db_result(success: bool, error: str = None):
    """記錄 DB 操作結果（Step 4）"""
    if _current_trace:
        _current_trace.db_success = success
        _current_trace.db_error = error
        
        if not success:
            _current_trace.action_taken = "skipped"
            _current_trace.skip_reason = "db_error"


def save_trace():
    """將當前 trace 存入資料庫"""
    if not _current_trace:
        return
    
    try:
        from app import db
        db.insert_memory_trace(_current_trace)
    except Exception as e:
        print(f"[memory_trace] 儲存 trace 失敗: {e}")
    finally:
        clear_trace()
