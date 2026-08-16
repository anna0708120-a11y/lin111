"""
组装整个 app：建 FastAPI 实例、挂路由、挂首页、启动主动消息的定时巡检。

这是唯一一个"知道所有模块"的文件，其他模块（state / llm / persona /
agent / notify / web.routes）之间尽量不互相依赖，只依赖 config 和 state。

V4: 新增 Intimacy Scheduler（24 小時自動 tick）
"""
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.agent.proactive import run_proactive_check, run_memory_review
from app.web.frontend import HTML_CONTENT
from app.web.routes import router
from app.integrations.hermes_routes import router as hermes_router
from app.integrations.hermes_management_proxy import router as hermes_management_router
from app.integrations.hermes_settings_routes import router as hermes_settings_router
from app.web.spaces_routes import router as spaces_router
from app.state import state

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(hermes_router)
app.include_router(hermes_management_router)
app.include_router(hermes_settings_router)
app.include_router(spaces_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def home():
    return HTMLResponse(content=HTML_CONTENT)


scheduler = BackgroundScheduler()
scheduler.add_job(
    run_proactive_check,
    "interval",
    minutes=config.PROACTIVE_CHECK_EVERY_MINUTES,
)
scheduler.add_job(
    run_memory_review,
    "interval",
    days=7,
)

# V4: 啟動 Intimacy Tick Scheduler（每 10 分鐘自動 tick）
def intimacy_tick_job():
    """定時 tick 任務（用於 BackgroundScheduler）"""
    from datetime import datetime
    from app.intimacy.tick import tick_and_update
    from app.intimacy.dream import maybe_create_dream_trigger
    
    now = datetime.now()
    
    # 1. 推進身體狀態
    tick_and_update(state, now)
    
    # 2. 檢查夢境觸發
    last_message_at = getattr(state, 'last_anchor_at', None)
    if maybe_create_dream_trigger(state, now, last_message_at):
        seed = getattr(state, 'last_dream_seed', None)
        if seed:
            # V4.1: 記錄到夢境歷史
            from app.intimacy.dream import apply_dream_after_effect
            deltas = apply_dream_after_effect(state, seed.tags)
            
            if hasattr(state, 'dream_history'):
                state.dream_history.add_dream(seed, now, deltas)
            
            state.add_log("dream", f"夢境觸發：{seed.theme}")

scheduler.add_job(
    intimacy_tick_job,
    "interval",
    minutes=10,
)

def life_runtime_tick_job():
    """Phase 7 autonomous reconciliation; it never enables send_message."""
    if not config.LIFE_RUNTIME_ENABLED:
        return
    from app.life.phase7 import drain_outbox, run_life_runtime_tick
    run_life_runtime_tick()
    drain_outbox()


scheduler.add_job(
    life_runtime_tick_job,
    "interval",
    minutes=config.LIFE_RUNTIME_TICK_MINUTES,
)

scheduler.start()
