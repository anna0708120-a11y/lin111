"""
Railway 目前是靠这个文件启动的（相当于执行 python main.py）。
真正的 app 定义都搬进了 app/ 文件夹（app/main.py 才是"组装"的地方），
这里只留一个很薄的入口，保证部署方式完全不用改，你也不用去 Railway 改任何设置。
"""
import os

import uvicorn

from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
