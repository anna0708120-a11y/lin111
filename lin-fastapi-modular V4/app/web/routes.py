"""
所有对外的 API 路由。这里只负责"网络请求 <-> 各模块函数"的转接，
本身不写业务逻辑；业务逻辑都在 agent / state / notify 里。

以后 Flutter app 要接进来，看这个文件就知道有哪些接口能打。
"""
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from app import db
from app.agent.brain import generate_reply
from app.notify.bark import send_to_bark
from app.state import state
from app.web.pwa import MANIFEST_JSON, SERVICE_WORKER_JS

router = APIRouter()


class Activity(BaseModel):
    activity: str
    app_name: Optional[str] = None


class MemoryItem(BaseModel):
    category: str
    content: str
    tag: Optional[str] = None


class ProactiveSettings(BaseModel):
    enabled: Optional[bool] = None
    min_minutes: Optional[int] = None
    max_minutes: Optional[int] = None


class AvatarPayload(BaseModel):
    data: str
    who: Optional[str] = "lin"  # "lin" 或 "anna"


@router.get("/health")
def health():
    """给 Render / 之后的监控用的健康检查接口，顺便回报 Supabase 有没有连上。"""
    return {"status": "ok", "supabase_connected": db.is_connected()}


@router.get("/manifest.json")
def manifest():
    return Response(content=MANIFEST_JSON, media_type="application/manifest+json")


@router.get("/sw.js")
def service_worker():
    return Response(content=SERVICE_WORKER_JS, media_type="application/javascript")


@router.post("/watch")
def observe_anna(activity: Activity):
    if activity.app_name and activity.app_name != "聊天界面":
        if not state.check_app_cooldown(activity.app_name):
            return {"status": "Cooldown", "message": ""}
        state.update_app_cooldown(activity.app_name)
        context = f"Anna刚打开了{activity.app_name}"
    else:
        context = f"Anna说：{activity.activity}"

    reply, thinking = generate_reply(context, app_name=activity.app_name, use_cache=False)
    send_to_bark(reply)

    state.mark_conversation_anchor()
    state.add_log("監控觸發", f"{activity.app_name or '聊天'}: {activity.activity[:30]}")
    return {"status": "Success", "message": reply, "thinking": thinking}


@router.get("/logs")
def get_logs():
    return {
        "logs": state.activity_log[-20:],
        "notes": state.chen_notes[-15:],
        "quota": state.daily_count.get("count", 0),
    }


@router.get("/memory")
def list_memory():
    """给记忆库分页面用：回传目前所有记忆（来自 Supabase，不是浏览器本地存的）。"""
    return {"memories": state.memory_bank}


@router.post("/memory")
def add_memory(item: MemoryItem):
    # 手动存的记忆默认给5星（Anna自己选择要记的，视为重要），关键字留空表示不参与自动去重比对
    memory_id = state.add_memory(item.tag or item.category, item.content, category=item.category, importance=5)
    state.add_log("記憶新增", f"[{item.category}] {item.content[:30]}")
    return {"status": "Success", "id": memory_id}


@router.delete("/memory/{memory_id}")
def remove_memory(memory_id: int):
    state.delete_memory(memory_id)
    return {"status": "Success"}


@router.post("/note")
def add_note(content: dict):
    state.add_note(content.get("text", ""))
    return {"status": "Success"}


@router.get("/settings")
def get_settings():
    """给之后的设置面板 / Flutter app 用：查看目前的主动消息设置。"""
    return {"push": state.proactive}


@router.post("/settings")
def update_settings(payload: ProactiveSettings):
    """给之后的设置面板 / Flutter app 用：更新主动消息设置（开关、静默区间）。"""
    state.update_proactive(
        enabled=payload.enabled,
        min_minutes=payload.min_minutes,
        max_minutes=payload.max_minutes,
    )
    return {"push": state.proactive}


@router.get("/mood")
def get_mood():
    """给状态面板用：Lin目前的状态自评。"""
    return {"mood": state.mood}


@router.get("/avatar")
def get_avatar(who: str = "lin"):
    return {"avatar": state.anna_avatar if who == "anna" else state.lin_avatar}


@router.post("/avatar")
def set_avatar(payload: AvatarPayload):
    state.set_avatar(payload.who, payload.data)
    return {"status": "Success"}


@router.delete("/avatar")
def delete_avatar(who: str = "lin"):
    state.clear_avatar(who)
    return {"status": "Success"}
