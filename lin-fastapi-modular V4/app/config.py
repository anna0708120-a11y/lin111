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
# thinking mode：开了之后回应会带独立的 reasoning_content（真思考），不用再靠prompt装格式
DEEPSEEK_REASONING_EFFORT = os.getenv("DEEPSEEK_REASONING_EFFORT", "high")
# thinking mode 的思考内容也算在这个token数里，调太小思考会被截断
DEEPSEEK_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", 1200))
# 真的 thinking mode（不是靠prompt装格式），"high"比较平衡，"max"更慢更贵
DEEPSEEK_REASONING_EFFORT = os.getenv("DEEPSEEK_REASONING_EFFORT", "high")
# thinking mode 的输出包含推理+正文一起算token，180太容易被截断，调高一点
DEEPSEEK_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", 1200))

# ---- Bark 推送 ----
# 想同时推给手机+电脑，就在 Render 环境变量填 BARK_KEYS，两个key用逗号隔开，
# 例如：BARK_KEYS=手机的key,电脑的key
# 只填一个也没关系，旧的 BARK_KEY 变量还继续有效。
_raw_bark_keys = os.getenv("BARK_KEYS", "") or os.getenv("BARK_KEY", "")
BARK_KEYS = [k.strip() for k in _raw_bark_keys.split(",") if k.strip()]
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

# ---- Supabase（长期记忆 + 状态持久化）----
# 两个都留空的话，app 会自动退回纯内存模式，照样能跑，只是重启就忘记。
# SUPABASE_KEY 请填 service_role key（在 Supabase 项目 API 设置里），不是 anon key。
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
