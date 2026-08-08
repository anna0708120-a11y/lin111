"""Groq-backed candidate detector for Phase 2B memory decisions."""
import json
import re

import requests

from app import config
from app.memory_intent import detect_memory_intent

GROQ_MEMORY_DETECTOR_SYSTEM = """你是长期记忆候选检测器，不负责聊天，也不执行数据库操作。
只判断用户这句话是否有足够证据进入长期记忆。

remember：明确偏好、明确事实、明确长期状态，或用户明确要求记住。
no：一次性事件、当下评价、临时情绪、普通寒暄、对他人/对象的描述，或明显不属于用户长期信息。
uncertain：证据不足、歧义明显、无法确认是否为用户长期信息。

禁止根据单个关键词推断长期偏好。不要展示 reasoning。
只输出一个 JSON 对象，不要 Markdown：
{"decision":"remember|no|uncertain","tag":"","keyword":"","summary":"","reason":""}
"""


def coarse_memory_candidate(user_text):
    """Cheap local gate: only send plausible memory candidates to Groq."""
    text = (user_text or "").strip()
    if not text:
        return False
    if detect_memory_intent(text)["explicit"]:
        return True
    patterns = (
        r"(?:我|我自己)(?:很|最)?(?:喜欢|喜歡|不喜欢|不喜歡|爱|愛|讨厌|討厭)",
        r"(?:我|我的)(?:是|叫|住在|来自|來自|从事|從事|有|没有|沒有)",
        r"(?:我一直|我通常|我习惯|我習慣|我会|我會)",
        r"(?:以后|以後)(?:我|我的)",
    )
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _parse_json(content):
    if not content:
        return None
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def detect_memory_candidate(user_text):
    """Return remember/no/uncertain without exposing model reasoning."""
    text = (user_text or "").strip()
    if not coarse_memory_candidate(text):
        return {"decision": "no", "tag": "", "keyword": "", "summary": "", "reason": "coarse_gate"}

    if not config.GROQ_API_KEY:
        # Explicit intent remains deterministic when the optional detector is unavailable.
        intent = detect_memory_intent(text)
        if intent["explicit"]:
            fact = intent["fact"]
            return {"decision": "remember", "tag": "用户明确要求", "keyword": fact[:50], "summary": fact, "reason": "explicit_intent"}
        return {"decision": "uncertain", "tag": "", "keyword": "", "summary": "", "reason": "groq_not_configured"}

    payload = {
        "model": config.GROQ_MEMORY_MODEL,
        "messages": [
            {"role": "system", "content": GROQ_MEMORY_DETECTOR_SYSTEM},
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,
        "max_tokens": 180,
        "reasoning_effort": "low",
        "include_reasoning": False,
        "response_format": {"type": "json_object"},
    }
    try:
        response = requests.post(
            f"{config.GROQ_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=12,
        )
        response.raise_for_status()
        body = response.json()
        content = body.get("choices", [{}])[0].get("message", {}).get("content")
        result = _parse_json(content) or {}
        decision = str(result.get("decision", "uncertain")).lower()
        if decision not in {"remember", "no", "uncertain"}:
            decision = "uncertain"
        if decision != "remember":
            return {"decision": decision, "tag": "", "keyword": "", "summary": "", "reason": "detector"}
        return {
            "decision": "remember",
            "tag": str(result.get("tag") or "长期记忆").strip()[:30],
            "keyword": str(result.get("keyword") or text).strip()[:50],
            "summary": str(result.get("summary") or text).strip(),
            "reason": "detector",
        }
    except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
        print(f"[groq_memory_detector] request failed: {exc}")
        return {"decision": "uncertain", "tag": "", "keyword": "", "summary": "", "reason": "detector_error"}


def candidate_to_parser_text(candidate):
    """Render a detector candidate through Lin's existing Memory Decision parser."""
    if not candidate or candidate.get("decision") != "remember":
        return ""
    return """[MEMORY_DECISION]
worth_remembering: yes
action: create
importance: 3
category: 长期记忆
tag: {tag}
keyword: {keyword}
summary: {summary}
[/MEMORY_DECISION]""".format(
        tag=str(candidate.get("tag") or "长期记忆").replace("\n", " "),
        keyword=str(candidate.get("keyword") or "").replace("\n", " "),
        summary=str(candidate.get("summary") or "").replace("\n", " "),
    )


