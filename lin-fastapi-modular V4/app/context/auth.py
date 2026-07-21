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
        # 没设置token时直接拒绝所有请求，不能放行——
        # 不然只要Render忘记设这个环境变量，所有上传接口就对全网公开、没有任何验证。
        raise HTTPException(status_code=503, detail="CONTEXT_API_TOKEN not configured on server")

    expected = f"Bearer {config.CONTEXT_API_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="unauthorized")
    return True
