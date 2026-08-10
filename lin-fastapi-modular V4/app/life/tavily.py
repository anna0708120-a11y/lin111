"""Read-only Tavily adapter for the Phase 9 Tool Brain."""
from __future__ import annotations

from typing import Any

import requests

from app import config


def search(query: str, *, max_results: int = 5) -> dict[str, Any]:
    if not config.TAVILY_API_KEY:
        return {"ok": False, "error": "tavily_not_configured", "results": []}
    try:
        response = requests.post(
            config.TAVILY_BASE_URL,
            json={
                "api_key": config.TAVILY_API_KEY,
                "query": str(query)[:500],
                "max_results": max(1, min(int(max_results), 10)),
                "search_depth": "basic",
                "include_answer": True,
            },
            timeout=config.TOOL_BRAIN_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        rows = [
            {"title": item.get("title"), "url": item.get("url"), "content": item.get("content", "")[:1200]}
            for item in payload.get("results", [])
            if isinstance(item, dict)
        ]
        return {"ok": True, "answer": payload.get("answer"), "results": rows}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:500], "results": []}
