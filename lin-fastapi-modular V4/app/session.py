"""
聊天室（Session）管理模块

参考 Claude 官方界面：
- 左上角三条线图标 → 打开侧边栏
- New chat → 开启新聊天室
- Recent → 显示最近的聊天室列表

每个聊天室都是独立上下文，但共享记忆库。
"""
import uuid
from datetime import datetime
from typing import Optional
from app import db

def generate_session_id() -> str:
    """生成新的 session ID"""
    return str(uuid.uuid4())

def create_new_session() -> dict:
    """创建新聊天室，返回 session 信息"""
    session_id = generate_session_id()
    now = datetime.now().isoformat()
    
    session = {
        "id": session_id,
        "title": "新对话",
        "created_at": now,
        "updated_at": now,
        "message_count": 0
    }
    
    # 保存到数据库
    if db._client:
        try:
            db._client.table("chat_sessions").insert(session).execute()
        except Exception as e:
            print(f"[session] 创建 session 失败: {e}")
    
    return session

def get_session_list(limit: int = 20) -> list:
    """获取最近的聊天室列表"""
    if not db._client:
        return []
    
    try:
        res = (
            db._client.table("chat_sessions")
            .select("id, title, created_at, updated_at, message_count, starred")
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[session] 读取 session 列表失败: {e}")
        return []

def toggle_star_session(session_id: str) -> bool:
    """切换聊天室的置顶（starred）状态，返回切换后的状态"""
    if not db._client:
        return False
    
    try:
        res = db._client.table("chat_sessions").select("starred").eq("id", session_id).execute()
        current = bool(res.data[0]["starred"]) if res.data else False
        new_value = not current
        
        db._client.table("chat_sessions").update({
            "starred": new_value
        }).eq("id", session_id).execute()
        
        return new_value
    except Exception as e:
        print(f"[session] 切换 session 置顶状态失败: {e}")
        return False

def update_session_title(session_id: str, title: str):
    """更新聊天室标题（根据首条消息自动生成）"""
    if not db._client:
        return
    
    try:
        db._client.table("chat_sessions").update({
            "title": title,
            "updated_at": datetime.now().isoformat()
        }).eq("id", session_id).execute()
    except Exception as e:
        print(f"[session] 更新 session 标题失败: {e}")

def update_session_activity(session_id: str):
    """更新聊天室活跃时间和消息计数"""
    if not db._client:
        return
    
    try:
        # 先获取当前消息数
        res = db._client.table("chat_sessions").select("message_count").eq("id", session_id).execute()
        current_count = res.data[0]["message_count"] if res.data else 0
        
        db._client.table("chat_sessions").update({
            "updated_at": datetime.now().isoformat(),
            "message_count": current_count + 1
        }).eq("id", session_id).execute()
    except Exception as e:
        print(f"[session] 更新 session 活跃度失败: {e}")

def delete_session(session_id: str):
    """删除聊天室（包括其所有消息）"""
    if not db._client:
        return
    
    try:
        # 删除该 session 的所有消息
        db._client.table("conversation_history").delete().eq("session_id", session_id).execute()
        
        # 删除 session 记录
        db._client.table("chat_sessions").delete().eq("id", session_id).execute()
    except Exception as e:
        print(f"[session] 删除 session 失败: {e}")

def get_default_session() -> str:
    """获取默认 session（如果没有任何 session，创建一个）"""
    sessions = get_session_list(limit=1)
    
    if not sessions:
        new_session = create_new_session()
        return new_session["id"]
    
    return sessions[0]["id"]
