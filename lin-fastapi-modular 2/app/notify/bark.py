"""
Bark 推送封装。

原本的写法是把消息直接拼进 URL 路径发 GET 请求，遇到中文标点或特殊符号
容易出问题；这里改成 Bark 官方推荐的 POST + JSON body，更稳。

以后想同时支持别的推送方式（比如网页 Web Push、Flutter app 自己的推送），
在这个文件夹 (app/notify/) 里加新文件、加新函数就好，
调用的地方 (agent/proactive.py, web/routes.py) 不用改。
"""
import requests

from app import config
from app.state import state


def send_to_bark(message, title="Lin"):
    if not config.BARK_KEY or not message:
        return
    try:
        requests.post(
            f"{config.BARK_BASE_URL}/{config.BARK_KEY}",
            json={"title": title, "body": message},
            timeout=5,
        )
        state.add_log("推送", message)
    except Exception as e:
        print(f"[bark] 推送失败: {e}")
