import json
"""
Lin 的"大脑"：把人设(persona) + 记忆(state) + 现实状态(context) + 模型(llm) 串起来，产出一句回复。

不管这轮触发是 Anna 主动发消息、监控到她开了某个 app、
还是 agent/initiative.py 判断"该主动找她了"，最终都走这一个函数。

现在用 DeepSeek 原生 thinking mode：reasoning_content 是真思考，不用再切字符串。
思考内容最后面会藏两段结构化判断（记忆判定、状态自评），处理完之后从"给Anna看的思考内容"里拿掉。
"""
import random
from datetime import datetime, timedelta

from app import config
from app.state import state
from app.llm.deepseek_client import call_deepseek
from app.persona import build_system_prompt
from app.memory_rules import parse_memory_decision, parse_mood_report, strip_hidden_blocks
from app.context.provider import get_context, format_context_for_prompt

FALLBACK_REPLIES = ["还没走远。", "嗯。", "我看着你。"]

def generate_reply(context, app_name=None, use_cache=True):
    """
    返回 (reply_text, thinking_text)。
    thinking_text 是清理过、可以直接显示给Anna看的思考内容；命中缓存或没配置API key时是 None。
    """
    if use_cache and state.last_context_cache == context and state.last_reply_at:
        if datetime.now() - state.last_reply_at < timedelta(minutes=2):
            return random.choice(FALLBACK_REPLIES), None

    if not state.check_rate_limit():
        return "今天额度用完了，或者刚刚问太快了，等一下再说。", None

    memory_summary = state.recent_memory_text()
    # 获取对话历史并格式化成易读文本
    conv_list = state.get_recent_conversation(n=20)
    if conv_list:
        formatted = []
        for turn in conv_list:
            role_name = "Anna" if turn["role"] == "anna" else "Lin"
            formatted.append(f"{role_name}：{turn['content']}")
        conversation_history = "\n".join(formatted)
    else:
        conversation_history = ""
    # 每个来源内部都有自己的缓存（天气30分钟、Mac/日历/屏幕时间/定位都是读最新一条快照），
    # 这里不用担心每次生成回复都会打一堆外部API——大部分时候只是读 Supabase 里的一条记录。
    # 某个来源没开启、没数据、或抓取失败，会自动不出现在结果里，不会塞垃圾进prompt。
    world_context = format_context_for_prompt(get_context())
    system_prompt = build_system_prompt(context, memory_summary, world_context, conversation_history)

    content, reasoning = call_deepseek(system_prompt, max_tokens=config.DEEPSEEK_MAX_TOKENS)
    state.record_call()

    if not content:
        return "信号不好。", None

    thinking_display = None
    if reasoning:
        decision = parse_memory_decision(reasoning)
        if decision:
            state.remember_or_reinforce(decision)

        mood = parse_mood_report(reasoning)
        if mood:
            state.update_mood(mood)

        thinking_display = strip_hidden_blocks(reasoning) or None

    state.last_context_cache = context
    state.mark_reply()
    state.add_log("AI回复", f"成功：{content[:40]}...")
    return content, thinking_display

def write_daily_journal():
    """
    每天一篇，不是每条消息都写。让Lin看着记忆自己写今天的感想，
    不带thinking mode（这本来就是要写进正文的东西，不需要再分离一层思考）。
    """
    if state.has_written_journal_today():
        return
    today_conversation = state.get_today_conversation_text()
    if today_conversation:
        context = (
            "写一篇今天的日记。回顾一下今天你们之间发生的事、你的感受，写成你自己的反思，不是转述系统日志。\n"
            "以下是今天你们之间真实发生的对话记录，只能基于这些真实内容来写，"
            "不要编造没有发生过的事情、没说过的话、没做过的事：\n"
            f"{today_conversation}"
        )
    else:
        context = (
            "今天你们之间没有发生任何对话或互动。写一篇简短的日记，"
            "可以写你自己的心情、想法、或者对Anna的想念，"
            "但不要编造今天发生了什么具体的事情——因为今天真的什么都没发生。"
        )
    system_prompt = build_system_prompt(context, state.recent_memory_text())
    content, _ = call_deepseek(system_prompt, max_tokens=config.DEEPSEEK_MAX_TOKENS, thinking=False)
    state.record_call()
    if content:
        state.add_note(content)
    state.mark_journal_written()
    

def generate_reply_stream(context, app_name=None, use_cache=True):
    """
    流式生成回覆，yield SSE 格式的事件。
    """
    import json
    from app.llm.deepseek_client import call_deepseek_stream
    from app.memory_rules import parse_memory_decision, parse_mood_report, strip_hidden_blocks
    
    if not state.check_rate_limit():
        err_msg = "今天额度用完了，或者刚刚问太快了，等一下再说。"
        yield "event: error\n"
        yieln.dumps({"message": err_msg})
        yield "\n\n"
        yield "event: don    return
    
    if use_cache and state.last_context_cache == context and state.last_reply_at:
        if datetime.now() - state.last_reply_at < timedelta(minutes=2):
            fallback = random.choice(FALLBACK_REPLIES)
            yie          yield json.dumps({"delta": fallback})
            yield "\n\nevent: don    return
    
    memory_summary = state.recent_memory_text()
    conv_list = state.get_recent_conversation(n=20)
    if conv_list:
        formatted = []
        for turn in conv_list:
            role_name = "Anna" if turn["role"] == "anna" else "Lin"
            formatted.append(f"{role_name}：{turn['content']}")
        conversation_history = "\n".join(formatted)
    else:
        conversation_history = ""
    
    from app.context.provider import get_context, format_context_for_prompt
    world_context = format_context_for_prompt(get_context())
    system_prompt = build_system_prompt(context, memory_summary, world_context, conversation_history)
    
    state.record_call()
    
    full_reasoning = ""
    full_content = ""
    
    try:
        for event_type, data in call_deepseek_stream(system_prompt, max_tokens=config.DEEPSEEK_MAX_TOKENS):
            if event_type == "reasoning":
                full_reasoning += data
                yield "event: yield json.dumps({"content": data})
                yield "\n\n"
                
            elif event_type == "content":
                full_content += data
                yield "event:ield json.dumps({"delta": data})
                yield "\n\n"
                
            elif event_type == "done":
                if full_reasoning:
                    decision = parse_memory_decision(full_reasoning)
                    if decision:
                        state.remember_or_reinforce(decision)
                    
                    mood = parse_mood_report(full_reasoning)
                    if mood:
                        state.update_mood(mood)
                
                state.last_context_cache = context
                state.mark_reply()
                state.add_log("AI回复", f"成功：{full_content[:40]}...")
                
                if full_content and full_content not in ("信号不好。", "今天额度用完了，或者刚刚问太快了，等一下再说。"):
                    thinking_display = strip_hidden_blocks(full_reasoning) if full_reasoning else None
                    state.add_conversation_turn("lin", full_content, thinking=thinking_display)
                    
                    from app.notify.bark import send_to_bark
                    send_to_bark(full_content)
                
                state.mark_conversation_anchor()
                yield "eveield json.dumps(data)
                yield "\n\n"
                
            elif event_type == "error":
                yield "eveyield json.dumps({"message": data})
                yield "\n\nevent: don          
    except Exception as e:
        print(f"[brain] Stream error: {e}")
        yield "event: erson.dumps({"message": "信号不好。"})
        yield "\n\nevent: done\ndata: {}\n\n"






