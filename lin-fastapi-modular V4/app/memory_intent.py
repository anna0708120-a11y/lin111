"""Backend-owned detection for explicit user memory requests."""
import json
import re

from app.llm.deepseek_client import call_deepseek


_MEMORY_REQUEST_PATTERNS = (
    r"记住(?:我|我的)?(?P<fact>.+)",
    r"記住(?:我|我的)?(?P<fact>.+)",
    r"請記住(?:我|我的)?(?P<fact>.+)",
    r"请记住(?:我|我的)?(?P<fact>.+)",
    r"帮我记住(?:我|我的)?(?P<fact>.+)",
    r"幫我記住(?:我|我的)?(?P<fact>.+)",
    r"把(?:我|我的)?(?P<fact>.+)记住",
    r"把(?:我|我的)?(?P<fact>.+)記住",
)


def detect_memory_intent(user_text):
    """Return the user fact only when the user explicitly asks to remember it."""
    text = (user_text or "").strip()
    for pattern in _MEMORY_REQUEST_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fact = match.group("fact").strip(" \t\r\n，。,.!?！？:：")
            if fact:
                return {"explicit": True, "fact": fact, "source": text}
    return {"explicit": False, "fact": None, "source": text}


def _json_object(text):
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def build_memory_decision(user_text):
    """Build a create decision; backend intent, not the model, controls execution."""
    intent = detect_memory_intent(user_text)
    if not intent["explicit"]:
        return None

    fact = intent["fact"]
    prompt = (
        "只为一条用户明确要求保存的记忆生成字段，不要判断是否保存。\n"
        "只输出 JSON：{\"tag\":\"\",\"keyword\":\"\",\"summary\":\"\"}\n"
        f"用户原话：{fact}"
    )
    content, _ = call_deepseek(prompt, thinking=False, temperature=0.2, max_tokens=256)
    fields = _json_object(content) or {}
    tag = str(fields.get("tag") or "偏好").strip()[:30]
    keyword = str(fields.get("keyword") or fact).strip()[:50]
    summary = str(fields.get("summary") or fact).strip()
    return {
        "action": "create",
        "importance": 3,
        "category": "长期记忆",
        "tag": tag,
        "keyword": keyword,
        "summary": summary,
    }
