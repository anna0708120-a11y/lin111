"""
所有环境变量 / 配置集中在这里。

以后要加 Supabase、要接 Flutter 后台、要调主动消息的默认间隔，
都只改这一个文件，不用去别的模块里翻。
"""
import os
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _load_polaris_config():
    """Load non-secret runtime settings from Polaris before constants are built."""
    base_url = os.getenv("POLARIS_SERVER_URL", "").rstrip("/")
    if not base_url:
        return {}
    namespace = os.getenv("POLARIS_CONFIG_NAMESPACE", "lin")
    group = os.getenv("POLARIS_CONFIG_GROUP", "LIN")
    file_name = os.getenv("POLARIS_CONFIG_FILE", "lin-runtime.json")
    query = urlencode({"namespace": namespace, "group": group, "fileName": file_name, "version": "0"})
    try:
        request = Request(f"{base_url}/config/v1/GetConfigFile?{query}", headers={"Accept": "application/json"})
        with urlopen(request, timeout=float(os.getenv("POLARIS_CONFIG_TIMEOUT", "5"))) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = payload.get("configFile", {}).get("content")
        values = json.loads(content) if content else {}
        if not isinstance(values, dict):
            raise ValueError("Polaris config content must be a JSON object")
        print(f"[polaris] loaded {namespace}/{group}/{file_name} version {payload.get('configFile', {}).get('version', '?')}")
        return values
    except Exception as exc:
        print(f"[polaris] config unavailable, using environment defaults: {exc}")
        return {}


_POLARIS_CONFIG = _load_polaris_config()


def _setting(env_name, config_name, default):
    return os.getenv(env_name, _POLARIS_CONFIG.get(config_name, default))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 本地没装 python-dotenv 也没关系，Railway 上环境变量是平台直接注入的
    pass

# ---- 主聊天模型 Provider Routing ----
# DeepSeek 主聊天默认走官方 API；GPT / Claude 可选模型继续走 A6API。
# Groq Memory Detector 使用独立配置，不经过这个 routing。
MAIN_LLM_API_KEY = os.getenv("A6API_API_KEY", "")
MAIN_LLM_BASE_URL = os.getenv("A6API_BASE_URL", "https://api.a6api.com/v1")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEFAULT_PROVIDER = str(_setting("DEFAULT_PROVIDER", "default_provider", "deepseek")).lower()
DEFAULT_MODEL = _setting("DEFAULT_MODEL", "default_model", "deepseek-v4-flash")
MAIN_LLM_REASONING_EFFORT = _setting("MAIN_LLM_REASONING_EFFORT", "main_llm_reasoning_effort", "high")
MAIN_LLM_TIMEOUT = int(_setting("MAIN_LLM_TIMEOUT", "main_llm_timeout", 45))
MAIN_LLM_MAX_TOKENS = int(_setting("MAIN_LLM_MAX_TOKENS", "main_llm_max_tokens", 1200))

# Provider alias 是后续 UI 的稳定接口；实际 model ID 只在配置层维护。
PROVIDER_MODELS = {
    "gpt": os.getenv("GPT_MODEL", "gpt-5.6-terra"),
    "claude": os.getenv("CLAUDE_MODEL", "claude-sonnet-5"),
    "deepseek": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
}

# 支持的模型目录，不被 brain.py 直接引用。
MODEL_CATALOG = {
    "gpt-5.6-terra": "gpt",
    "gpt-5.6-luna": "gpt",
    "gpt-5.4-mini": "gpt",
    "claude-sonnet-5": "claude",
    "claude-haiku-4-5": "claude",
    "deepseek-v4-flash": "deepseek",
}

MAIN_PROVIDERS = {
    "gpt": {"capabilities": {"chat": True, "streaming": True, "reasoning": True, "structured_output": True, "tool_calling": False}},
    "claude": {"capabilities": {"chat": True, "streaming": True, "reasoning": True, "structured_output": True, "tool_calling": False}},
    "deepseek": {"capabilities": {"chat": True, "streaming": True, "reasoning": True, "structured_output": True, "tool_calling": False}},
}

# 旧 DeepSeek client 的兼容配置；主聊天已由 main_router 负责。
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_REASONING_EFFORT = MAIN_LLM_REASONING_EFFORT
DEEPSEEK_MAX_TOKENS = MAIN_LLM_MAX_TOKENS

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MEMORY_MODEL = os.getenv("GROQ_MEMORY_MODEL", "openai/gpt-oss-20b")

# ---- Gemma auxiliary inference (Ollama Cloud-compatible) ----
GEMMA_BASE_URL = os.getenv("GEMMA_BASE_URL", "https://ollama.com/api").rstrip("/")
GEMMA_API_KEY = os.getenv("GEMMA_API_KEY", "")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "")
GEMMA_TIMEOUT_SECONDS = int(os.getenv("GEMMA_TIMEOUT_SECONDS", "20"))

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
PROACTIVE_ENABLED_DEFAULT = str(_setting("PROACTIVE_ENABLED_DEFAULT", "proactive_enabled_default", True)).lower() == "true"
PROACTIVE_MIN_MINUTES = int(_setting("PROACTIVE_MIN_MINUTES", "proactive_min_minutes", 90))
PROACTIVE_MAX_MINUTES = int(_setting("PROACTIVE_MAX_MINUTES", "proactive_max_minutes", 240))
PROACTIVE_CHECK_EVERY_MINUTES = int(_setting("PROACTIVE_CHECK_EVERY_MINUTES", "proactive_check_every_minutes", 5))

# ---- Phase 7 Life Runtime ----
LIFE_RUNTIME_ENABLED = str(_setting("LIFE_RUNTIME_ENABLED", "life_runtime_enabled", "true")).lower() == "true"
LIFE_RUNTIME_TICK_MINUTES = int(_setting("LIFE_RUNTIME_TICK_MINUTES", "life_runtime_tick_minutes", 5))
LIFE_SEND_ENABLED = str(_setting("LIFE_SEND_ENABLED", "life_send_enabled", "false")).lower() == "true"

# ---- Phase 9 Tool Brain ----
TOOL_BRAIN_ENABLED = str(_setting("TOOL_BRAIN_ENABLED", "tool_brain_enabled", "false")).lower() == "true"
TOOL_BRAIN_TIMEOUT_SECONDS = int(os.getenv("TOOL_BRAIN_TIMEOUT_SECONDS", 30))
GROQ_TOOL_BRAIN_API_KEY = os.getenv("GROQ_TOOL_BRAIN_API_KEY", "")
GROQ_TOOL_BRAIN_BASE_URL = os.getenv("GROQ_TOOL_BRAIN_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_TOOL_BRAIN_MODEL = os.getenv("GROQ_TOOL_BRAIN_MODEL", "openai/gpt-oss-120b")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_BASE_URL = os.getenv("TAVILY_BASE_URL", "https://api.tavily.com/search")

# ---- 速率限制 / 冷却 ----
DAILY_QUOTA = int(os.getenv("DAILY_QUOTA", 180))
RPM_LIMIT = int(os.getenv("RPM_LIMIT", 8))
APP_COOLDOWN_MINUTES = int(os.getenv("APP_COOLDOWN_MINUTES", 20))

# ---- Supabase（长期记忆 + 状态持久化）----
# 两个都留空的话，app 会自动退回纯内存模式，照样能跑，只是重启就忘记。
# SUPABASE_KEY 请填 service_role key（在 Supabase 项目 API 设置里），不是 anon key。
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# ---- 聊天记录持久化（跨装置同步用）----
# 手机 dock / 电脑 dock / 网页版，三端现在都从 Supabase 读同一份聊天记录，不再各自存在浏览器 localStorage 里。
# 保留条数做成配置项，以后觉得 500 太少，改这个数字就好，不用动数据库结构。
CHAT_HISTORY_LIMIT = int(_setting("CHAT_HISTORY_LIMIT", "chat_history_limit", 500))

# ---- Context Provider 总开关（每个功能都能单独关，改.env就好，不用删代码） ----
ENABLE_MAC = str(_setting("ENABLE_MAC", "enable_mac", "true")).lower() == "true"
ENABLE_WEATHER = str(_setting("ENABLE_WEATHER", "enable_weather", "true")).lower() == "true"
ENABLE_CALENDAR = str(_setting("ENABLE_CALENDAR", "enable_calendar", "true")).lower() == "true"
ENABLE_SCREENTIME = str(_setting("ENABLE_SCREENTIME", "enable_screentime", "true")).lower() == "true"
ENABLE_LOCATION = str(_setting("ENABLE_LOCATION", "enable_location", "true")).lower() == "true"
ENABLE_PHOTO = str(_setting("ENABLE_PHOTO", "enable_photo", "true")).lower() == "true"

# ---- Context API 统一鉴权 Token ----
# Mac / iPhone快捷指令 / 以后第二台电脑，全部共用这一个token
# 用 Bearer Token 方式：请求header加 Authorization: Bearer 这个值
CONTEXT_API_TOKEN = os.getenv("CONTEXT_API_TOKEN", "")

# ---- Read-only Render -> Hermes Lin Context Bridge ----
LIN_CONTEXT_API_TOKEN = os.getenv("LIN_CONTEXT_API_TOKEN", "")
LIN_CONTEXT_TTL_SECONDS = int(os.getenv("LIN_CONTEXT_TTL_SECONDS", "900"))
LIN_CONTEXT_CONVERSATION_LIMIT = int(os.getenv("LIN_CONTEXT_CONVERSATION_LIMIT", "12"))
LIN_CONTEXT_MEMORY_LIMIT = int(os.getenv("LIN_CONTEXT_MEMORY_LIMIT", "8"))
LIN_CONTEXT_LIFE_EVENT_LIMIT = int(os.getenv("LIN_CONTEXT_LIFE_EVENT_LIMIT", "8"))
HERMES_CALLBACK_API_TOKEN = os.getenv("HERMES_CALLBACK_API_TOKEN", "")

# ---- 天气：定位坐标（用 WEATHER_LAT / WEATHER_LON 环境变量设置） ----
WEATHER_LAT = os.getenv("WEATHER_LAT", "25.0330")   # 默认台北
WEATHER_LON = os.getenv("WEATHER_LON", "121.5654")
WEATHER_CACHE_MINUTES = int(os.getenv("WEATHER_CACHE_MINUTES", 30))

# ---- Apple Calendar 公开订阅链接（webcal:// 要换成 https://） ----
ICAL_URL = os.getenv("ICAL_URL", "")
CALENDAR_CACHE_MINUTES = int(os.getenv("CALENDAR_CACHE_MINUTES", 15))

# ---- Supabase Storage 附件桶（Phase 8；私人桶，URL 由后端按需签发）----
ATTACHMENT_BUCKET = os.getenv("ATTACHMENT_BUCKET", "attachments")

# ---- Supabase Storage 图片桶名字 ----
PHOTO_BUCKET = os.getenv("PHOTO_BUCKET", "photos")

# ---- ElevenLabs 语音（免费额度，非商用，用现成音色不是克隆）----
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
# 去 ElevenLabs 网站的 Voice Library 挑一个音色，网址或后台能看到 voice_id，填这里
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
# 免费额度只有10,000字/月，单条message别送太长，超过这个长度直接拒绝，避免一条訊息就把额度花光
TTS_MAX_CHARS = int(os.getenv("TTS_MAX_CHARS", 200))
# Supabase Storage 放语音档的桶名字
VOICE_BUCKET = os.getenv("VOICE_BUCKET", "voices")
