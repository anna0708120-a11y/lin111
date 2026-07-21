"""
组装整个 app：建 FastAPI 实例、挂路由、挂首页、启动主动消息的定时巡检。

这是唯一一个"知道所有模块"的文件，其他模块（state / llm / persona /
agent / notify / web.routes）之间尽量不互相依赖，只依赖 config 和 state。
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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
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
scheduler.start()
