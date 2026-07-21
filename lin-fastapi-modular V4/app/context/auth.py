"""
统一的 Context API 鉴权。
所有"上传数据进来"的接口（Mac状态、定位、图片等）都共用同一个检查方式：
请求的 header 要带 Authorization: Bearer <CONTEXT_API_TOKEN>
以后不管是 Mac、iPhone 快捷指令、或第二台电脑，都用同一个token，不用每个功能各写一套。
"""
from fastapi import Header, HTTPException

from app import config

def verify_context_token(authorization: str = Header(default="")):
    """FastAPI 依赖注入用：接口签名里加一个参数就自动检查。"""
    if not config.CONTEXT_API_TOKEN:
        # 没设置token时（比如你还没配置好），先放行，但会在log提醒
        print("[context.auth] 警告：CONTEXT_API_TOKEN 尚未设置，接口目前不设防")
        return True

    expected = f"Bearer {config.CONTEXT_API_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="unauthorized")
    return True
