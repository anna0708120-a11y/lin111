"""Standalone Lin spaces page with additive navigation cards.

The group-chat card only links to the configured existing group-chat route. It
never owns or modifies group-chat UI, transport, AI bindings, or data.
"""

from __future__ import annotations

import os

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["lin-spaces"])


def _safe_group_chat_url() -> str:
    value = os.getenv("LIN_GROUP_CHAT_URL", "/group-chat").strip()
    return value if value.startswith(("/", "http://", "https://")) else "/group-chat"


@router.get("/spaces")
def spaces_page() -> HTMLResponse:
    group_url = _safe_group_chat_url()
    return HTMLResponse(content=f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lin</title><link rel="stylesheet" href="/static/lin-spaces.css"></head>
<body><main class="shell"><header><a class="back" href="/">Lin</a><p>你的地方</p></header>
<section class="grid">
<a class="card group" href="{group_url}"><span class="eyebrow">一起</span><h1>群聊</h1><p>進入原本的群聊。</p><span class="arrow">↗</span></a>
<a class="card diary" href="/notes"><span class="eyebrow">留下</span><h2>日記</h2><p>收起今天的片段。</p><span class="arrow">↗</span></a>
<a class="card time" href="/events"><span class="eyebrow">此刻</span><h2>時間</h2><p>看見正在發生的事。</p><span class="arrow">↗</span></a>
<a class="card quote" href="/memory"><span class="eyebrow">收藏</span><h2>最喜歡的話</h2><p>回到想留下的句子。</p><span class="arrow">↗</span></a>
<a class="card settings" href="/agent-settings"><span class="eyebrow">管理</span><h2>設定</h2><p>Hermes Agent 與工具能力。</p><span class="arrow">↗</span></a>
<a class="card whisper" href="/"><span class="eyebrow">只說給你聽</span><h2>悄悄話</h2><p>回到 Lin 的對話。</p><span class="arrow">↗</span></a>
</section></main></body></html>""")


@router.get("/agent-settings")
def agent_settings_page() -> HTMLResponse:
    return HTMLResponse(content="""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lin 設定</title><link rel="stylesheet" href="/static/lin-spaces.css"></head>
<body><main class="shell settings-shell"><header><a class="back" href="/spaces">Lin</a><p>Agent 設定</p></header>
<div id="runtime-state" class="runtime-state">正在讀取 Hermes Runtime...</div>
<section class="setting-grid">
<article><h2>Agent</h2><p>執行狀態與模型路由。</p></article><article><h2>Tools</h2><p>可用工具能力。</p></article>
<article><h2>Toolsets</h2><p>工具集合與啟用範圍。</p></article><article><h2>Skills</h2><p>Hermes Skills 管理。</p></article>
<article><h2>MCP</h2><p>MCP Server 連線管理。</p></article><article><h2>Model / Provider</h2><p>Hermes 執行模型設定。</p></article>
<article><h2>Skill Settings</h2><p><code>skills.config.*</code> 設定。</p></article>
</section></main><script src="/static/js/hermes_settings.js"></script></body></html>""")
