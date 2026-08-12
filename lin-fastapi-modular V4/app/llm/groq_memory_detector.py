"""Groq-backed candidate detector for Phase 2B memory decisions."""
import json
import re

import requests

from app import config
from app.memory_intent import detect_memory_intent

GROQ_MEMORY_DETECTOR_SYSTEM = """你是 Memory Lifecycle 决策器，不负责聊天，也不执行数据库操作。
你只判断用户的新信息是否值得写入，以及与【相关记忆】中候选记忆的关系。

没有候选记忆时：明确偏好、明确事实、明确长期状态，或用户明确要求记住，才可 create；
单次事件、当下评价、临时情绪、普通寒暄、对他人/对象的描述，必须 none；证据不足必须 none。
有候选记忆时：同一稳定事实被明确再次确认才 reinforce；同一事实的明确状态变化才 update；
明显矛盾但无法安全地直接覆盖或封存旧记忆才 conflict；明确表示旧事实取消、失效或不再成立才 archive。
候选只是线索，不是修改指令。没有足够证据必须 none。

以下规则必须严格遵守：
- “看到猫”或“觉得一只猫可爱”不等于喜欢猫。
- “今天心情好”不等于长期状态。
- “以前喜欢”不等于现在仍喜欢；出现过去与现在相反的信息时选 none 或 conflict。
- “最近觉得咖啡好喝”不足以证明稳定偏好，选 none。
- 不要根据单个关键词或对象提及推断长期偏好。
- reinforce/update/conflict/archive 只能填写【相关记忆】中提供的 memory_id，不能编造。
只输出一个 JSON 对象，不要 Markdown：
{"action":"create|reinforce|update|conflict|archive|none","memory_id":null,"tag":"","keyword":"","summary":"","reason":""}
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
        r"(?:我一直|我通常|我平时|我平時|我习惯|我習慣|我会|我會|我都會)",
        r"(?:最近|近来|近來).*(?:觉得|覺得|感觉|感覺|好喝|好吃|喜欢|喜歡)",
        r"(?:以前|之前|曾经|曾經).*(?:现在|現在|但现在|但現在)",
        r"(?:看到|遇到|听到|聽到).*(?:不过|不過|但是|但).*(?:没|沒有|不)",
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


def detect_memory_candidate(user_text, candidates=None):
    """Return a backend-validated lifecycle candidate without exposing model reasoning."""
    text = (user_text or "").strip()
    if not coarse_memory_candidate(text):
        return {"action": "none", "decision": "no", "memory_id": None, "tag": "", "keyword": "", "summary": "", "reason": "coarse_gate"}

    if not config.GEMMA_API_KEY or not config.GEMMA_MODEL:
        intent = detect_memory_intent(text)
        if intent["explicit"]:
            fact = intent["fact"]
            return {"action": "create", "decision": "remember", "memory_id": None, "tag": "用户明确要求", "keyword": fact[:50], "summary": fact, "reason": "explicit_intent"}
        return {"action": "none", "decision": "uncertain", "memory_id": None, "tag": "", "keyword": "", "summary": "", "reason": "gemma_not_configured"}

    candidate_text = "\n".join(
        "ID:{id} | source:{created_by} | keyword:{keyword} | {content}".format(
            id=memory.get("id", ""),
            created_by=memory.get("created_by", "user"),
            keyword=memory.get("keyword", ""),
            content=memory.get("content", ""),
        )
        for memory in (candidates or [])
    ) or "（没有相关记忆）"
    payload = {
        "model": config.GEMMA_MODEL,
        "messages": [
            {"role": "system", "content": GROQ_MEMORY_DETECTOR_SYSTEM},
            {"role": "user", "content": f"用户新消息：{text}\n\n【相关记忆】\n{candidate_text}"},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1, "num_predict": 180},
    }
    try:
        response = requests.post(
            f"{config.GEMMA_BASE_URL}/chat",
            headers={
                "Authorization": f"Bearer {config.GEMMA_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=config.GEMMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
        result = _parse_json(body.get("message", {}).get("content")) or {}
        model_decision = str(result.get("decision", "")).lower()
        action = str(result.get("action") or {"remember": "create", "no": "none", "uncertain": "none"}.get(model_decision, "none")).lower()
        if action not in {"create", "reinforce", "update", "conflict", "archive", "none"}:
            action = "none"
        legacy_decision = model_decision if model_decision in {"remember", "no", "uncertain"} else ("remember" if action == "create" else "no")

        memory_id = result.get("memory_id")
        try:
            memory_id = int(memory_id) if memory_id is not None else None
        except (TypeError, ValueError):
            memory_id = None
        candidate_ids = {memory.get("id") for memory in (candidates or [])}
        if action in {"reinforce", "update", "conflict", "archive"} and memory_id not in candidate_ids:
            return {"action": "none", "decision": "uncertain", "memory_id": None, "tag": "", "keyword": "", "summary": "", "reason": "invalid_lifecycle_target"}
        if action == "none":
            return {"action": "none", "decision": legacy_decision, "memory_id": None, "tag": "", "keyword": "", "summary": "", "reason": "detector"}
        return {
            "action": action,
            "decision": legacy_decision,
            "memory_id": memory_id,
            "tag": str(result.get("tag") or "长期记忆").strip()[:30],
            "keyword": str(result.get("keyword") or text).strip()[:50],
            "summary": str(result.get("summary") or text).strip(),
            "reason": "detector",
        }
    except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
        print(f"[groq_memory_detector] request failed: {exc}")
        return {"action": "none", "decision": "uncertain", "memory_id": None, "tag": "", "keyword": "", "summary": "", "reason": "detector_error"}


def candidate_to_parser_text(candidate):
    """Render a lifecycle candidate through Lin's existing Memory Decision parser."""
    if not candidate or (candidate.get("action") == "none" and candidate.get("decision") != "remember"):
        return ""
    action = candidate.get("action") or ("create" if candidate.get("decision") == "remember" else "none")
    return """[MEMORY_DECISION]
worth_remembering: yes
action: {action}
importance: 3
category: 长期记忆
tag: {tag}
keyword: {keyword}
memory_id: {memory_id}
summary: {summary}
[/MEMORY_DECISION]""".format(
        action=str(action),
        tag=str(candidate.get("tag") or "长期记忆").replace("\n", " "),
        keyword=str(candidate.get("keyword") or "").replace("\n", " "),
        memory_id="" if candidate.get("memory_id") is None else candidate["memory_id"],
        summary=str(candidate.get("summary") or "").replace("\n", " "),
    )


