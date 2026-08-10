"""OpenAI-compatible Groq Tool Brain client returning constrained JSON only."""
from __future__ import annotations

import json
from typing import Any

import requests

from app import config

_ALLOWED = {"no_tool", "search"}


def decide(candidate: dict[str, Any]) -> dict[str, Any]:
    if not config.TOOL_BRAIN_ENABLED or not config.GROQ_TOOL_BRAIN_API_KEY:
        return {"ok": False, "decision": "no_tool", "reason": "tool_brain_not_configured"}
    prompt = {
        "task": "You are a backend tool planner, not a companion. Return JSON only.",
        "allowed_decisions": ["no_tool", "search"],
        "constraints": [
            "Never send a message.",
            "Never modify memory, mood, or life state.",
            "Use search only when external current information is necessary.",
        ],
        "candidate": {
            "route": candidate.get("route"),
            "category": candidate.get("category"),
            "context": candidate.get("context_snapshot", {}),
        },
        "output": {"decision": "no_tool|search", "reason": "short string", "query": "required only for search"},
    }
    try:
        response = requests.post(
            f"{config.GROQ_TOOL_BRAIN_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {config.GROQ_TOOL_BRAIN_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": config.GROQ_TOOL_BRAIN_MODEL,
                "messages": [{"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            timeout=config.TOOL_BRAIN_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"].get("content") or "{}"
        parsed = json.loads(content)
        decision = str(parsed.get("decision") or "no_tool")
        if decision not in _ALLOWED:
            decision = "no_tool"
        query = str(parsed.get("query") or "")[:500]
        if decision == "search" and not query:
            decision = "no_tool"
        return {"ok": True, "decision": decision, "reason": str(parsed.get("reason") or "")[:240], "query": query}
    except Exception as exc:
        return {"ok": False, "decision": "no_tool", "reason": f"tool_brain_error:{str(exc)[:300]}"}
