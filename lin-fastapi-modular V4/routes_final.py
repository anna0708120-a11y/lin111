"""
所有对外的 API 路由。这里只负责"网络请求 <-> 各模块函数"的转接，
本身不写业务逻辑；业务逻辑都在 agent / state / notify 里。

以后 Flutter app 要接进来，看这个文件就知道有哪些接口能打。
"""
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel

from app import db
from app.agent.brain import generate_reply
from app.context.auth import verify_context_token
from app.context import mac as mac_context
from app.notify.bark import send_to_bark
from app.state import state
from app.web.pwa import MANIFEST_JSON, SERVICE_WORKER_JS

router = APIRouter()

class Activity(BaseModel):
    activity: str
    app_name: Optional[str] = None
    image: Optional[str] = None  # base64 图片数据

class MemoryItem(BaseModel):
    category: str
    content: str
    tag: Optional[str] = None

class ProactiveSettings(BaseModel):
    enabled: Optional[bool] = None
    min_minutes: Optional[int] = None
    max_minutes: Optional[int] = None

class AvatarPayload(BaseModel):
    who: Optional[str] = "lin"  # "lin" 或 "anna"
    data: Optional[str] = None  # base64 图片数据

class MacStatus(BaseModel):
    """mac_daemon.py 会定期打这个进来。字段都设成可选，
    以后daemon想加别的信息（比如前台app名字）不用改这里的接口。"""
    cpu: Optional[float] = None
    ram: Optional[float] = None
    battery: Optional[int] = None
    charging: Optional[bool] = None
    locked: Optional[bool] = None
    asleep: Optional[bool] = None


class ScreenTimePayload(BaseModel):
    """iPhone 快捷指令定期上传屏幕使用时间。字段都设成可选。"""
    total_minutes: Optional[int] = None
    date: Optional[str] = None  # YYYY-MM-DD

class LocationPayload(BaseModel):
    """iPhone 快捷指令上传定位。字段都设成可选。"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    label: Optional[str] = None  # 地点名称（如果有的话）
    accuracy: Optional[float] = None

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
        # 处理图片消息
        if activity.image:
            context = f"Anna发了一张图片"
            if activity.activity and activity.activity != '[图片]':
                context += f"，并说: {activity.activity}"
            state.add_conversation_turn("anna", context, image_data=activity.image)
        else:
            context = f"Anna说：{activity.activity}"
            state.add_conversation_turn("anna", activity.activity)

    reply, thinking = generate_reply(context, app_name=activity.app_name, use_cache=False)
    send_to_bark(reply)

    # 只有真的生成了回复内容，才记进对话历史（避免额度用完/信号不好时把错误提示当成Lin说的话存进去）
    if reply and reply not in ("信号不好。", "今天额度用完了，或者刚刚问太快了，等一下再说。"):
        state.add_conversation_turn("lin", reply, thinking=thinking)

    state.mark_conversation_anchor()
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

@router.post("/context/mac", dependencies=[Depends(verify_context_token)])
def update_mac_status(payload: MacStatus):
    """
    mac_daemon.py（第4步）定期上传Mac状态，存进 context_state 表的 source='mac'。
    需要 header: Authorization: Bearer <CONTEXT_API_TOKEN>，没带对会直接403/401
    （鉴权逻辑集中在 app/context/auth.py，见 verify_context_token）。
    """
    mac_context.save_mac_status(payload.dict(exclude_none=True))
    return {"status": "Success"}


@router.post("/context/screentime", dependencies=[Depends(verify_context_token)])
def update_screentime(payload: ScreenTimePayload):
    """
    iPhone 快捷指令定期上传屏幕使用时间，存进 context_state 表的 source='screentime'。
    需要 header: Authorization: Bearer <CONTEXT_API_TOKEN>。
    """
    from app.context import screentime as screentime_context
    screentime_context.save_screentime(payload.dict(exclude_none=True))
    return {"status": "Success"}

@router.post("/context/location", dependencies=[Depends(verify_context_token)])
def update_location(payload: LocationPayload):
    """
    iPhone 快捷指令上传定位，存进 context_state 表的 source='location'。
    需要 header: Authorization: Bearer <CONTEXT_API_TOKEN>。
    """
    from app.context import location as location_context
    location_context.save_location(payload.dict(exclude_none=True))
    return {"status": "Success"}


# ========== 经期记录 API ==========
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List

class PeriodRecord(BaseModel):
    date: str  # YYYY-MM-DD

@router.get("/period")
def get_period_data():
    """
    获取经期记录数据和周期预测。
    返回: { records: [日期数组], cycle: 平均周期天数 }
    """
    from app import db
    
    records = []
    try:
        # 新格式：透過 save_context 存入 payload.dates 陣列
        cached = db.load_context("period")
        if cached and cached.get("payload") and cached["payload"].get("dates"):
            records = cached["payload"]["dates"]
        else:
            # 舊格式相容：直接從 context_state 的 data 欄位讀取（最多一個日期）
            result = db.supabase.table('context_state').select('data').eq('source', 'period').limit(1).execute()
            if hasattr(result, 'data') and result.data:
                row = result.data[0]
                if row.get('data') and row['data'].get('date'):
                    records.append(row['data']['date'])
    except Exception as e:
        print(f"Load period records failed: {e}")
    
    cycle = 28
    if len(records) >= 2:
        sorted_records = sorted(records)
        diffs = []
        for i in range(1, len(sorted_records)):
            d1 = datetime.strptime(sorted_records[i-1], '%Y-%m-%d')
            d2 = datetime.strptime(sorted_records[i], '%Y-%m-%d')
            diffs.append((d2 - d1).days)
        if diffs:
            cycle = int(sum(diffs) / len(diffs))
    
    return {"records": sorted(records, reverse=True), "cycle": cycle}


@router.post("/period")
def record_period(payload: PeriodRecord):
    """
    记录经期日期。
    存入 context_state 表，所有日期存放在 payload.dates 陣列中。
    """
    from app import db
    
    try:
        datetime.strptime(payload.date, '%Y-%m-%d')
        
        # 讀取現有記錄，新舊格式都支援（migration）
        cached = db.load_context("period")
        records = []
        if cached and cached.get("payload") and cached["payload"].get("dates"):
            records = cached["payload"]["dates"]
        else:
            # 舊格式相容：讀取 data 欄位中的單一日期
            result = db.supabase.table('context_state').select('data').eq('source', 'period').limit(1).execute()
            if hasattr(result, 'data') and result.data:
                row = result.data[0]
                if row.get('data') and row['data'].get('date'):
                    records.append(row['data']['date'])
        
        # 防重複：只有日期不存在時才加入
        if payload.date not in records:
            records.append(payload.date)
            records.sort()
        
        # 寫入新格式：單行 payload.dates 陣列（upsert）
        db.save_context("period", {"dates": records})
        
        return {"status": "Success", "date": payload.date}
    except ValueError:
        return {"status": "Error", "message": "Invalid date format, use YYYY-MM-DD"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}


@router.delete("/period/{date}")
def delete_period(date: str):
    """
    删除指定日期的经期记录。
    """
    from app import db
    
    try:
        datetime.strptime(date, '%Y-%m-%d')
        
        # 讀取現有記錄（新格式）
        cached = db.load_context("period")
        records = []
        if cached and cached.get("payload") and cached["payload"].get("dates"):
            records = cached["payload"]["dates"]
        
        # 移除該日期
        if date in records:
            records.remove(date)
        
        # 寫回
        db.save_context("period", {"dates": records})
        
        return {"status": "Success", "date": date}
    except ValueError:
        return {"status": "Error", "message": "Invalid date format"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}



# Model management
@router.get("/models")
def list_models():
    from app.llm.provider_factory import list_available_models
    models = list_available_models()
    return {"current": state.current_model, "models": models}

@router.post("/models/switch")
def switch_model(data: dict):
    model_id = data.get("model_id")
    if not model_id:
        return {"status": "Error", "message": "Missing model_id"}
    from app.llm.provider_factory import list_available_models
    available = [m["id"] for m in list_available_models() if m["available"]]
    if model_id not in available:
        return {"status": "Error", "message": "Model not available"}
    state.current_model = model_id
    return {"status": "Success", "current": state.current_model}

@router.post("/chat/stream")
async def chat_stream(activity: Activity):
    from app.agent.brain import generate_reply_stream
    from app import send_to_bark
    
    if activity.app_name and activity.app_name != "聊天界面":
        if not state.check_app_cooldown(activity.app_name):
            return Response(content="Cooldown", status_code=429)
        state.update_app_cooldown(activity.app_name)
        context = f"Anna刚打开了{activity.app_name}"
    else:
        if activity.image:
            context = "Anna发了一张图片"
            if activity.activity and activity.activity != '[图片]':
                context += f"，并说: {activity.activity}"
            state.add_conversation_turn("anna", context, image_data=activity.image)
        else:
            context = f"Anna说：{activity.activity}"
            state.add_conversation_turn("anna", activity.activity)
    
    async def event_generator():
        try:
            full_content = []
            full_thinking = []
            for chunk in generate_reply_stream(context, app_name=activity.app_name):
                if 'token' in chunk:
                    full_content.append(chunk['token'])
                    msg = json.dumps({'type': 'token', 'content': chunk['token']}, ensure_ascii=False)
                    yield f"data: {msg}\n\n"
                elif 'thinking_token' in chunk:
                    full_thinking.append(chunk['thinking_token'])
                    msg = json.dumps({'type': 'thinking', 'content': chunk['thinking_token']}, ensure_ascii=False)
                    yield f" {msg}\n\n"
                elif 'error' in chunk:
                    msg = json.dumps({'type': 'error', 'message': chunk['error']}, ensure_ascii=False)
                    yield f"data: {msg}\n\n"
                    return
                elif 'done' in chunk:
                    break
                await asyncio.sleep(0)
            
            reply = ''.join(full_content).strip()
            thinking = ''.join(full_thinking).strip() if full_thinking else None
            send_to_bark(reply)
            
            if reply and reply not in ("信号不好。", "今天额度用完了，或者刚刚问太快了，等一下再说。"):
                state.add_conversation_turn("lin", reply, thinking=thinking)
            
            state.mark_conversation_anchor()
            msg = json.dumps({'type': 'done', 'message': reply, 'thinking': thinking}, ensure_ascii=False)
            yield f"data: {msg}\n\n"
            
        except Exception as e:
            msg = json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)
            yield f"data: {msg}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
