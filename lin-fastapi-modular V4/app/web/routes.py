"""
所有对外的 API 路由。这里只负责"网络请求 <-> 各模块函数"的转接，
本身不写业务逻辑；业务逻辑都在 agent / state / notify 里。

以后 Flutter app 要接进来，看这个文件就知道有哪些接口能打。
"""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel

from app import db
from app.agent.brain import generate_reply, generate_reply_stream
from app.context.auth import verify_context_token
from app.context import mac as mac_context
from app.event_bus import event_bus
from app.notify.bark import send_to_bark
from app.state import state
from app.web.pwa import MANIFEST_JSON, SERVICE_WORKER_JS
from app.web.diagnose import DIAGNOSE_HTML

router = APIRouter()

class TTSPayload(BaseModel):
    text: str

class Activity(BaseModel):
    activity: str
    app_name: Optional[str] = None
    image: Optional[str] = None
    session_id: Optional[str] = None

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
    apps: Optional[list] = None  # [{"name": "Instagram", "minutes": 30}, ...]

class LocationPayload(BaseModel):
    """iPhone 快捷指令上传定位。字段都设成可选。"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    label: Optional[str] = None  # 地点名称（如果有的话）
    accuracy: Optional[float] = None

class DeviceEventPayload(BaseModel):
    """iPhone 捷徑統一上報 endpoint，所有欄位皆可選"""
    event_type: str  # 必填：battery/wifi/reminder/arrive_home/leave_home/charging/unplug/airpods/app_opened
    # 電量相關
    battery_level: Optional[int] = None  # 0-100
    battery_state: Optional[str] = None  # "charging" / "unplugged" / "full"
    # Wi-Fi
    wifi_ssid: Optional[str] = None
    wifi_connected: Optional[bool] = None
    # 提醒事項
    reminder_title: Optional[str] = None
    reminder_due: Optional[str] = None  # ISO 8601
    # 到家/離家
    location_event: Optional[str] = None  # "arrive_home" / "leave_home"
    # AirPods
    airpods_connected: Optional[bool] = None
    airpods_name: Optional[str] = None
    # App 自動化
    app_name: Optional[str] = None
    # 通用附加資訊
    note: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    label: Optional[str] = None  # 地点名称（如果有的话）
    accuracy: Optional[float] = None

@router.get("/health")
def health():
    """给 Render / 之后的监控用的健康检查接口，顺便回报 Supabase 有没有连上。"""
    return {"status": "ok", "supabase_connected": db.is_connected()}

@router.get("/developer")
def developer_page():
    """独立 Developer Console。"""
    return FileResponse("static/developer.html", media_type="text/html")

@router.get("/dev")
def developer_page_alias():
    return developer_page()

@router.get("/manifest.json")
def manifest():
    return Response(content=MANIFEST_JSON, media_type="application/manifest+json")

@router.get("/diagnose")
def diagnose_page():
    """臨時診斷頁：讀取真實 viewport / safe-area / .tab-bar 數值，驗證完成後可刪除。"""
    return Response(content=DIAGNOSE_HTML, media_type="text/html")

@router.get("/sw.js")
def service_worker():
    return Response(content=SERVICE_WORKER_JS, media_type="application/javascript")

@router.post("/watch")
def observe_anna(activity: Activity):
    """
    🔥 Streaming 版本：返回 SSE 流式回應
    """
    target_session_id = activity.session_id or state.current_session_id
    
    if activity.app_name and activity.app_name != "聊天界面":
        if not state.check_app_cooldown(activity.app_name):
            def empty_stream():
                yield "event: conten{\"delta\": \"\"}\n\n"
                yield "event: done\n {}\n\n"
            return StreamingResponse(empty_stream(), media_type="text/event-stream")
        
        state.update_app_cooldown(activity.app_name)
        context = f"Anna刚打开了{activity.app_name}"
    else:
        if hasattr(state, 'consent_dynamics') and activity.activity:
            from app.intimacy.consent_dynamics import detect_behavior_and_adjust
            detected_behavior = detect_behavior_and_adjust(
                activity.activity,
                state.consent_dynamics
            )
            if detected_behavior:
                state.add_log("consent", f"行為檢測: {detected_behavior}")
        
        if activity.image:
            context = f"Anna发了一张图片"
            if activity.activity and activity.activity != '[图片]':
                context += f"，并说: {activity.activity}"
            state.add_conversation_turn("anna", context, image_data=activity.image, session_id=target_session_id)
        else:
            context = f"Anna说：{activity.activity}"
            state.add_conversation_turn("anna", activity.activity, session_id=target_session_id)
    
    return StreamingResponse(
        generate_reply_stream(context, app_name=activity.app_name, use_cache=False, session_id=target_session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/events")
def get_events():
    """System Monitor Event Bus 快照，給 Home UI 使用。"""
    return event_bus.get_snapshot()

@router.get("/logs")
def get_logs():
    return {
        "logs": state.activity_log[-20:],
        "notes": state.chen_notes[-15:],
        "quota": state.daily_count.get("count", 0),
    }

@router.get("/intimacy")
def get_intimacy():
    """
    親密引擎狀態查詢（給 Home UI 的身體狀態卡片用）
    返回：關係階段、互動意願、親密氛圍、身體狀態（V2預留）
    """
    from app.intimacy.engine import get_intimacy_state
    return get_intimacy_state(state.mood)

@router.get("/intimacy/status")
def get_intimacy_status():
    """Return the backend-owned current Body State, cycle, event, and after effects."""
    from datetime import datetime
    from app.intimacy.status import build_intimacy_status_payload
    from app.intimacy.tick import tick_and_update

    now = datetime.now()
    tick_and_update(state, now)
    return build_intimacy_status_payload(state, now)

@router.get("/intimacy/consent")
def get_consent_dynamics():
    """
    V4.1: Consent 動態調整查詢
    返回當前互動意願及其影響因素
    """
    from datetime import datetime
    from app.intimacy.consent import calculate_consent, get_consent_level, get_consent_description
    from app.intimacy.tick import tick_and_update
    
    # 先 tick 確保數值最新
    tick_and_update(state, datetime.now())
    
    # 計算 Consent
    body_values = getattr(state, 'body_values', {})
    relationship = getattr(state, 'relationship', None)
    if relationship is None:
        relationship = {"safety": 50, "rapport": 50, "temperature": 50}
    consent_dynamics = getattr(state, 'consent_dynamics', None)
    
    base_consent = calculate_consent(state.mood, body_values, relationship)
    
    # 獲取動態調整
    adjustments_list = []
    total_adjustment = 0
    final_consent = base_consent
    
    if consent_dynamics:
        from app.intimacy.consent_dynamics import get_consent_with_dynamics
        final_consent = get_consent_with_dynamics(base_consent, consent_dynamics)
        total_adjustment = consent_dynamics.get_total_adjustment()
        
        # 獲取有效調整列表
        active = consent_dynamics.get_active_adjustments(datetime.now())
        for adj in sorted(active, key=lambda x: x.timestamp, reverse=True):
            effect = adj.get_current_effect(datetime.now())
            if abs(effect) > 0.5:  # 只顯示有明顯效果的
                hours_ago = (datetime.now() - adj.timestamp).total_seconds() / 3600.0
                adjustments_list.append({
                    "reason": adj.reason,
                    "effect": round(effect, 1),
                    "hours_ago": round(hours_ago, 1),
                    "decay_progress": round((hours_ago / adj.decay_hours) * 100, 1) if adj.decay_hours > 0 else 100
                })
    
    consent_level = get_consent_level(final_consent)
    consent_desc = get_consent_description(final_consent, state.mood, body_values, relationship)
    
    return {
        "base_consent": round(base_consent, 1),
        "total_adjustment": round(total_adjustment, 1),
        "final_consent": round(final_consent, 1),
        "level": consent_level,
        "description": consent_desc,
        "adjustments": adjustments_list
    }

@router.get("/intimacy/events")
def get_intimacy_events(type: str = "all"):
    """
    V3：事件日誌時間軸（給「事件日誌」Tab 用）
    全部為架構預留假資料，V4 補上真實資料庫邏輯。
    """
    from app.intimacy.event_log import get_event_timeline
    return {"events": get_event_timeline(type)}

@router.get("/conversation")
def get_conversation():
    """
    给前端载入用：回传 Supabase 里存的共享聊天记录（不是浏览器 localStorage）。
    手机 dock / 电脑 dock / 网页版打开页面时都打这个接口，看到的是同一份记录，
    这样才能做到跨装置同步。
    """
    print("[CHAT-ID-2]", id(state.conversation_history))
    from datetime import datetime as _dt

    def _display_time(iso_str):
        if not iso_str:
            return ""
        try:
            return _dt.fromisoformat(iso_str).strftime("%H:%M")
        except Exception:
            return ""

    messages = []
    for idx, turn in enumerate(state.conversation_history):
        entry = {
            "r": "anna" if turn.get("role") == "anna" else "lin",
            "t": turn.get("content", ""),
            "iso": turn.get("time", ""),
            "time": _display_time(turn.get("time", "")),
            # 穩定掛載點用：優先用資料庫 row id，沒有的話（例如剛寫入、DB 還沒回填）fallback 用序號，
            # 不用隨機 id，保證同一份歷史多次渲染時掛載點一致。
            "message_id": turn.get("id") if turn.get("id") is not None else f"idx-{idx}",
        }
        if turn.get("thinking"):
            entry["think"] = turn["thinking"]
        if turn.get("trace"):
            entry["trace"] = turn["trace"]
        messages.append(entry)
    return {"messages": messages}

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
    需要 header: Authorization: Bearer <TOKEN>，没带对会直接403/401
    （鉴权逻辑集中在 app/context/auth.py，见 verify_context_token）。
    """
    mac_context.save_mac_status(payload.dict(exclude_none=True))
    # 組合人類可讀的訊息，寫入 Event Bus（Persistent，覆蓋）
    parts = []
    if payload.asleep is True:
        parts.append("Mac 休眠中")
    elif payload.locked is True:
        parts.append("Mac 已鎖定")
    else:
        parts.append("Mac 運作中")
    if payload.cpu is not None:
        parts.append(f"CPU {payload.cpu:.0f}%")
    if payload.ram is not None:
        parts.append(f"RAM {payload.ram:.0f}%")
    if payload.battery is not None:
        charging_str = " ⚡" if payload.charging else ""
        parts.append(f"電量 {payload.battery}%{charging_str}")
    event_bus.emit("mac", "  ·  ".join(parts))
    return {"status": "Success"}

@router.post("/context/screentime", dependencies=[Depends(verify_context_token)])
def update_screentime(payload: ScreenTimePayload):
    from app.context import screentime as screentime_context
    screentime_context.save_screentime(payload.dict(exclude_none=True))
    if payload.total_minutes is not None:
        hrs, mins = divmod(payload.total_minutes, 60)
        msg = f"今日螢幕使用 {hrs}h {mins}m" if hrs else f"今日螢幕使用 {mins}m"
        # 若有 app 明細，附上前3個
        if payload.apps:
            top = payload.apps[:3]
            app_str = "  |  ".join(f"{a.get('name','?')} {a.get('minutes','?')}m" for a in top)
            msg += f"  （{app_str}）"
        event_bus.emit("screentime", msg)
    return {"status": "Success"}

@router.post("/context/location", dependencies=[Depends(verify_context_token)])
def update_location(payload: LocationPayload):
    """
    iPhone 快捷指令上传定位，存进 context_state 表的 source='location'。
    需要 header: Authorization: Bearer <TOKEN>。
    """
    from app.context import location as location_context
    location_context.save_location(payload.dict(exclude_none=True))
    loc_label = payload.label or (f"{payload.latitude:.3f}, {payload.longitude:.3f}" if payload.latitude else "未知位置")
    event_bus.emit("location", f"目前位置：{loc_label}")
    return {"status": "Success"}

@router.post("/context/device", dependencies=[Depends(verify_context_token)])
def device_event(payload: DeviceEventPayload):
    """
    iPhone 捷徑統一上報 endpoint。
    所有手機感知事件（電量、Wi-Fi、提醒、到家/離家、充電、AirPods、App 自動化）
    都打這一支，依 event_type 分類寫入 Event Bus。
    Persistent 類（battery/wifi）覆蓋舊值；Activity 類（其餘）保留歷史。
    """
    t = payload.event_type

    if t == "battery":
        level = payload.battery_level
        state_str = {"charging": " ⚡充電中", "full": " ✅已充滿", "unplugged": ""}.get(payload.battery_state or "", "")
        if level is not None:
            event_bus.emit("app", f"📱 電量 {level}%{state_str}")

    elif t == "wifi":
        if payload.wifi_connected is False:
            event_bus.emit("app", "📶 Wi-Fi 已斷線")
        else:
            ssid = payload.wifi_ssid or "未知網路"
            event_bus.emit("app", f"📶 已連接 {ssid}")

    elif t == "reminder":
        title = payload.reminder_title or payload.note or "提醒事項"
        due = f"（{payload.reminder_due}）" if payload.reminder_due else ""
        event_bus.emit("system", f"🔔 提醒：{title}{due}")

    elif t in ("arrive_home", "leave_home"):
        emoji = "🏠" if t == "arrive_home" else "🚶"
        msg = "Anna 到家了" if t == "arrive_home" else "Anna 離家了"
        event_bus.emit("system", f"{emoji} {msg}")

    elif t == "charging":
        level = f"  {payload.battery_level}%" if payload.battery_level is not None else ""
        event_bus.emit("system", f"⚡ 開始充電{level}")

    elif t == "unplug":
        level = f"  {payload.battery_level}%" if payload.battery_level is not None else ""
        event_bus.emit("system", f"🔌 拔除充電{level}")

    elif t == "airpods":
        name = payload.airpods_name or "AirPods"
        if payload.airpods_connected is False:
            event_bus.emit("system", f"🎧 {name} 已斷開")
        else:
            event_bus.emit("system", f"🎧 {name} 已連接")

    elif t == "app_opened":
        app = payload.app_name or payload.note or "未知 App"
        event_bus.emit("system", f"📲 開啟 {app}")

    elif t == "status":
        # 定時上報：battery + wifi 一起打
        parts = []
        if payload.battery_level is not None:
            state_str = {"charging": "⚡", "full": "✅", "unplugged": ""}.get(payload.battery_state or "", "")
            parts.append(f"📱{payload.battery_level}%{state_str}")
        if payload.wifi_ssid:
            parts.append(f"📶{payload.wifi_ssid}")
        elif payload.wifi_connected is False:
            parts.append("📶離線")
        if parts:
            event_bus.emit("app", "  ".join(parts))

    else:
        # 未知類型，用 note 或 event_type 本身記錄
        event_bus.emit("system", payload.note or t)

    return {"status": "ok", "event_type": t}

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

# ========== 聊天记录配置 ==========
class ChatConfigPayload(BaseModel):
    """聊天记录数量配置"""
    limit: int

@router.get("/chat-config")
def get_chat_config():
    """获取当前聊天记录保留数量配置"""
    # 优先从 Supabase 读取用户设置的值
    cached = db.load_context("chat_config")
    if cached and cached.get("payload") and cached["payload"].get("limit"):
        limit = cached["payload"]["limit"]
    else:
        # 没有保存过，使用环境变量默认值
        from app.config import CHAT_HISTORY_LIMIT
        limit = CHAT_HISTORY_LIMIT
    return {"limit": limit}

@router.post("/chat-config")
def update_chat_config(payload: ChatConfigPayload):
    """更新聊天记录保留数量配置（立即生效）"""
    # 验证输入范围
    if payload.limit < 100 or payload.limit > 10000:
        return {"status": "Error", "message": "数量必须在 100-10000 之间"}
    
    try:
        # 调用 state 方法动态更新
        state.update_chat_history_limit(payload.limit)
        return {
            "status": "Success", 
            "limit": payload.limit,
            "message": "配置已更新并立即生效"
        }
    except Exception as e:
        return {"status": "Error", "message": str(e)}

# ========== 在一起日子配置 ==========
@router.get("/together-config")
def get_together_config():
    """获取在一起的开始日期和背景图"""
    config = db.load_context("together_config")
    if config and config.get("payload"):
        return config["payload"]
    else:
        # 默认返回今天作为开始日期
        from datetime import datetime
        return {
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "background_url": None
        }

class TogetherBackgroundPayload(BaseModel):
    image: str

@router.post("/together-background")
def update_together_background(payload: TogetherBackgroundPayload):
    """更新在一起卡片的背景图"""
    try:
        # 获取现有配置
        config = db.load_context("together_config")
        if config and config.get("payload"):
            data = config["payload"]
        else:
            from datetime import datetime
            data = {"start_date": datetime.now().strftime("%Y-%m-%d")}
        
        # 更新背景图
        data["background_url"] = payload.image
        
        # 保存到数据库
        db.save_context("together_config", data)
        
        return {"status": "Success", "message": "背景图已更新"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}

class TogetherStartDatePayload(BaseModel):
    start_date: str

@router.post("/together-start-date")
def update_together_start_date(payload: TogetherStartDatePayload):
    """设置在一起的开始日期"""
    try:
        # 获取现有配置
        config = db.load_context("together_config")
        if config and config.get("payload"):
            data = config["payload"]
        else:
            data = {"background_url": None}
        
        # 更新开始日期
        data["start_date"] = payload.start_date
        
        # 保存到数据库
        db.save_context("together_config", data)
        
        return {"status": "Success", "message": "开始日期已设置"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}


# ========== Session Management (多聊天室管理) ==========

@router.get("/sessions")
def get_sessions():
    """获取聊天室列表"""
    from app import session as session_module
    sessions = session_module.get_session_list()
    return {
        "sessions": sessions,
        "current_session_id": state.current_session_id
    }

@router.post("/sessions")
def create_session():
    """创建新聊天室"""
    new_session = state.create_new_session()
    return {"status": "Success", "session": new_session}

class SwitchSessionPayload(BaseModel):
    session_id: str

@router.post("/sessions/switch")
def switch_session(payload: SwitchSessionPayload):
    """切换到指定聊天室"""
    state.switch_session(payload.session_id)
    return {"status": "Success", "session_id": payload.session_id}

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """删除指定聊天室"""
    from app import session as session_module
    
    # 不能删除当前正在使用的 session
    if session_id == state.current_session_id:
        return {"status": "Error", "message": "无法删除当前正在使用的聊天室"}
    
    session_module.delete_session(session_id)
    return {"status": "Success", "message": "聊天室已删除"}

# ========== 前端侧边栏使用的会话 API ==========
@router.get("/chat-sessions")
def get_chat_sessions():
    """获取所有聊天会话列表（侧边栏用）"""
    from app import session as session_module
    
    sessions = session_module.get_session_list()
    # 格式化为前端需要的格式
    formatted_sessions = []
    for s in sessions:
        # 从数据库加载该 session 的第一条消息作为标题
        title = s.get("title", "新对话")
        
        # 格式化时间显示
        created_at = s.get("created_at", "")
        time_display = ""
        if created_at:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                now = datetime.now()
                diff = now - dt
                
                if diff.days == 0:
                    time_display = dt.strftime("%H:%M")
                elif diff.days == 1:
                    time_display = "昨天"
                elif diff.days < 7:
                    time_display = f"{diff.days}天前"
                else:
                    time_display = dt.strftime("%m/%d")
            except:
                time_display = created_at[:10]
        
        formatted_sessions.append({
            "id": s["id"],
            "title": title,
            "time": time_display,
            "message_count": s.get("message_count", 0),
            "starred": bool(s.get("starred", False))
        })
    
    return {"sessions": formatted_sessions}

@router.post("/chat-sessions")
def create_chat_session(payload: dict):
    """创建新的聊天会话"""
    new_session = state.create_new_session()
    return {
        "status": "Success",
        "session_id": new_session["id"],
        "session": new_session
    }

@router.get("/chat-sessions/{session_id}")
def get_chat_session(session_id: str):
    """获取指定会话的消息"""
    try:
        # 从数据库加载该 session 的所有消息
        conversations = db.load_conversations(limit=1000, session_id=session_id)
        
        # 格式化消息
        messages = []
        for conv in conversations:
            messages.append({
                "message_id": conv.get("id"),
                "role": conv.get("role", ""),
                "content": conv.get("content", ""),
                "thinking": conv.get("thinking"),
                "time": conv.get("created_at", ""),
                "trace": conv.get("trace")
            })
        
        return {
            "status": "Success",
            "messages": messages
        }
    except Exception as e:
        print(f"[get_chat_session] Error: {e}")
        return {"status": "Error", "message": "加载会话失败"}

@router.delete("/chat-sessions/{session_id}")
def delete_chat_session(session_id: str):
    """删除聊天会话（侧边栏用）"""
    from app import session as session_module
    
    if session_id == state.current_session_id:
        return {"status": "Error", "message": "无法删除当前正在使用的聊天室"}
    
    session_module.delete_session(session_id)
    return {"status": "Success"}

class RenameSessionPayload(BaseModel):
    title: str

@router.patch("/chat-sessions/{session_id}")
def rename_chat_session(session_id: str, payload: RenameSessionPayload):
    """重命名聊天会话（侧边栏用）"""
    from app import session as session_module

    title = (payload.title or "").strip()
    if not title:
        return {"status": "Error", "message": "标题不能为空"}

    session_module.update_session_title(session_id, title[:60])
    return {"status": "Success"}

@router.post("/chat-sessions/{session_id}/star")
def star_chat_session(session_id: str):
    """切换聊天室置顶（starred）状态（侧边栏用）"""
    from app import session as session_module

    new_state = session_module.toggle_star_session(session_id)
    return {"status": "Success", "starred": new_state}


@router.post("/tts")
def text_to_speech(payload: TTSPayload):
    """按需生成语音并回传公开音档 URL。"""
    from app.llm.tts_client import synth_speech

    audio_bytes = synth_speech(payload.text)
    if not audio_bytes:
        return {"status": "Failed", "url": None}
    filename = f"{uuid.uuid4().hex}.mp3"
    url = db.upload_voice(filename, audio_bytes)
    if not url:
        return {"status": "Failed", "url": None}
    return {"status": "Success", "url": url}
