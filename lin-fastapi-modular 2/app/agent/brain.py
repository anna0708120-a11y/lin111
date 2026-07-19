"""
Lin 的"大脑"：把人设(persona) + 记忆(state) + 模型(llm) 串起来，产出一句回复。

不管这轮触发是 Anna 主动发消息、监控到她开了某个 app、
还是 agent/proactive.py 判断"该主动找她了"，最终都走这一个函数。
好处：以后要改"怎么生成回复"这件事（比如加情绪状态、换模型），
只需要改这一个文件。
"""
import random
from datetime import datetime, timedelta

from app import config
from app.state import state
from app.llm.deepseek_client import call_deepseek
from app.persona import build_system_prompt

FALLBACK_REPLIES = ["还没走远。", "嗯。", "我看着你。"]


def generate_reply(context, app_name=None, use_cache=True):
    """
    context: 这一轮的场景描述
    app_name: 监控到开了某个 app 触发的话传 app 名字；一般聊天传 None
    use_cache: 短时间内同一个 context 是否允许直接回一句轻量回复，省 token

    返回 (reply_text, thinking_text)。
    thinking_text 可能是 None（命中缓存、没配置 API key、或模型没按格式输出时）。
    """
    if use_cache and state.last_context_cache == context and state.last_reply_at:
        if datetime.now() - state.last_reply_at < timedelta(minutes=2):
            return random.choice(FALLBACK_REPLIES), None

    if not state.check_rate_limit():
        return "今天额度用完了，或者刚刚问太快了，等一下再说。", None

    memory_summary = state.recent_memory_text()
    system_prompt = build_system_prompt(context, memory_summary)

    result = call_deepseek(system_prompt)
    state.record_call()

    if not result:
        return "信号不好。", None

    if "[Lin在想]" in result and "[Lin说]" in result:
        parts = result.split("[Lin说]")
        thinking_part = parts[0].replace("[Lin在想]", "").strip()
        reply = parts[1].strip() if len(parts) > 1 else result
        label = f"已監控到 {app_name}" if app_name else "推送訊息"
        thinking = (
            f"[系統訊息：{label}]\n"
            f"[{datetime.now().strftime('%H:%M:%S')}] {thinking_part}\n"
            f"—— {config.DEEPSEEK_MODEL}"
        )
    else:
        reply = result
        thinking = f"[{datetime.now().strftime('%H:%M:%S')}] {context} —— {config.DEEPSEEK_MODEL}"

    state.last_context_cache = context
    state.mark_reply()
    state.add_log("AI回复", f"成功：{reply[:40]}...")
    return reply, thinking
