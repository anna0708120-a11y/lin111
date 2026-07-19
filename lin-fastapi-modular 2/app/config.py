"""
所有环境变量 / 配置集中在这里。

以后要加 Supabase、要接 Flutter 后台、要调主动消息的默认间隔，
都只改这一个文件，不用去别的模块里翻。
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 本地没装 python-dotenv 也没关系，Railway 上环境变量是平台直接注入的
    pass

# ---- DeepSeek ----
# .env 或 Railway 的环境变量里填 DEEPSEEK_API_KEY，这里留空
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
# deepseek-chat / deepseek-reasoner 这两个旧名字会在 2026/07/24 下线，
# 新名字是 deepseek-v4-flash（快、便宜）和 deepseek-v4-pro（更强的推理/agent能力）
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions")

# ---- Bark 推送 ----
BARK_KEY = os.getenv("BARK_KEY", "")
BARK_BASE_URL = os.getenv("BARK_BASE_URL", "https://api.day.app")

# ---- Server ----
PORT = int(os.getenv("PORT", 8080))

# ---- 主动消息 (proactive) 默认设置 ----
# 之后可以透过 /settings 接口从前端改，或整个搬进 Supabase 的一张表
PROACTIVE_ENABLED_DEFAULT = True
PROACTIVE_MIN_MINUTES = int(os.getenv("PROACTIVE_MIN_MINUTES", 90))   # 至少静默这么久才考虑主动开口
PROACTIVE_MAX_MINUTES = int(os.getenv("PROACTIVE_MAX_MINUTES", 240))  # 静默超过这个数字，不管时段一定触发一次
PROACTIVE_CHECK_EVERY_MINUTES = int(os.getenv("PROACTIVE_CHECK_EVERY_MINUTES", 5))  # 后台巡检频率

# ---- 速率限制 / 冷却 ----
DAILY_QUOTA = int(os.getenv("DAILY_QUOTA", 180))
RPM_LIMIT = int(os.getenv("RPM_LIMIT", 8))
APP_COOLDOWN_MINUTES = int(os.getenv("APP_COOLDOWN_MINUTES", 20))

# ---- 预留给以后接 Supabase 用，现在留空不影响运行 ----
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
