"""
Mac 状态：由本地跑的小 daemon 每分钟上传一次（见 mac_daemon.py）。
这里只负责"读最新一条"给 provider 用，不负责收集。
"""
from app import config, db

def get_mac_status():
    if not config.ENABLE_MAC:
        return None
    cached = db.load_context("mac")
    return cached["payload"] if cached else None

def save_mac_status(payload):
    db.save_context("mac", payload)
