"""Backend-owned detection for explicit user memory requests."""
import re


_MEMORY_REQUEST_PATTERNS = (
    r"记住(?:我|我的)?(?P<fact>.+)",
    r"記住(?:我|我的)?(?P<fact>.+)",
    r"請記住(?:我|我的)?(?P<fact>.+)",
    r"请记住(?:我|我的)?(?P<fact>.+)",
    r"帮我记住(?:我|我的)?(?P<fact>.+)",
    r"幫我記住(?:我|我的)?(?P<fact>.+)",
    r"把(?:我|我的)?(?P<fact>.+)记住",
    r"把(?:我|我的)?(?P<fact>.+)記住",
    r"(?:以后|以後)(?:别|別|不要)忘记(?:我|我的)?(?P<fact>.+)",
    r"(?:以后|以後)(?:请|請)?记得(?:我|我的)?(?P<fact>.+)",
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


def build_memory_decision(user_text):
    """Build the existing memory decision shape for an explicit user request."""
    intent = detect_memory_intent(user_text)
    if not intent["explicit"]:
        return None

    fact = intent["fact"]
    return {
        "action": "create",
        "importance": 3,
        "category": "长期记忆",
        "tag": "用户明确要求",
        "keyword": fact[:50],
        "summary": fact,
    }
