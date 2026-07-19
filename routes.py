"""
所有对外的 API 路由。这里只负责"网络请求 <-> 各模块函数"的转接，
本身不写业务逻辑；业务逻辑都在 agent / state / notify 里。

以后 Flutter app 要接进来，看这个文件就知道有哪些接口能打。
"""
import random
import time
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.agent.brain import generate_reply
from app.notify.bark import send_to_bark
from app.state import state

router = APIRouter()


class Activity(BaseModel):
    activity: str
    app_name: Optional[str] = None


class MemoryItem(BaseModel):
    tag: str
    content: str


class ProactiveSettings(BaseModel):
    enabled: Optional[bool] = None
    min_minutes: Optional[int] = None
    max_minutes: Optional[int] = None


@router.get("/health")
def health():
    """给 Railway / 之后的监控用的健康检查接口。"""
    return {"status": "ok"}


@router.post("/watch")
def observe_anna(activity: Activity):
    if activity.app_name and activity.app_name != "聊天界面":
        if not state.check_app_cooldown(activity.app_name):
            return {"status": "Cooldown", "message": ""}
        state.update_app_cooldown(activity.app_name)
        context = f"Anna刚打开了{activity.app_name}"
    else:
        context = f"Anna说：{activity.activity}"

    time.sleep(random.uniform(2.0, 4.5))  # 保留原本"正在打字"的手感
    reply, thinking = generate_reply(context, app_name=activity.app_name, use_cache=False)
    if thinking:
        state.add_note(thinking)
    send_to_bark(reply)

    state.mark_conversation_anchor()
    state.add_log("監控觸發", f"{activity.app_name or '聊天'}: {activity.activity[:30]}")
    return {"status": "Success", "message": reply}


@router.get("/logs")
def get_logs():
    return {
        "logs": state.activity_log[-20:],
        "notes": state.chen_notes[-15:],
        "quota": state.daily_count.get("count", 0),
    }


@router.post("/memory")
def add_memory(item: MemoryItem):
    state.add_memory(item.tag, item.content)
    state.add_log("記憶新增", f"[{item.tag}] {item.content[:30]}")
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
    if payload.enabled is not None:
        state.proactive["enabled"] = payload.enabled
    if payload.min_minutes is not None:
        state.proactive["min_minutes"] = payload.min_minutes
    if payload.max_minutes is not None:
        state.proactive["max_minutes"] = payload.max_minutes
    return {"push": state.proactive}
