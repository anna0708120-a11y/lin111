"""
Lin 的"大脑"：把人设(persona) + 记忆(state) + 现实状态(context) + 模型(llm) 串起来，产出一句回复。

不管这轮触发是 Anna 主动发消息、监控到她开了某个 app、
还是 agent/initiative.py 判断"该主动找她了"，最终都走这一个函数。

现在用 DeepSeek 原生 thinking mode：reasoning_content 是真思考，不用再切字符串。
思考内容最后面会藏两段结构化判断（记忆判定、状态自评），处理完之后从"给Anna看的思考内容"里拿掉。
"""
import json
import random
from datetime import datetime, timedelta

from app import config
from app.state import state
from app.llm.deepseek_client import call_deepseek
from app.persona import build_system_prompt
from app.memory_rules import parse_memory_decision, parse_mood_event, strip_hidden_blocks
from app.context.provider import get_context, format_context_for_prompt
from app import mood_engine

FALLBACK_REPLIES = ["还没走远。", "嗯。", "我看着你。"]

def _auto_detect_mood_events(user_msg, lin_reply):
    """
    根據 user_msg 和 lin_reply 內容自動偵測情緒事件，不依賴 LLM 標籤。
    回傳事件列表，格式：[(event_name, level), ...]
    例如 [("PRAISE", "MEDIUM"), ("LONG_CHAT", "HIGH")]
    """
    events = []
    combined = (user_msg + " " + lin_reply).lower()
    
    # APOLOGY: sorry, 對不起, 抱歉
    if any(kw in combined for kw in ["sorry", "對不起", "对不起", "抱歉", "我錯", "我错"]):
        events.append(("APOLOGY", "MEDIUM"))
    
    # PRAISE: 誇讚、稱讚
    if any(kw in combined for kw in ["喜歡你", "喜欢你", "愛你", "爱你", "想你", "厲害", "厉害", "真棒", "好厲害", "好厉害"]):
        events.append(("PRAISE", "MEDIUM"))
    
    # COMFORT: 安慰
    if any(kw in combined for kw in ["沒事", "没事", "別怕", "别怕", "陪你", "抱抱", "親親", "亲亲"]):
        events.append(("COMFORT", "MEDIUM"))
    
    # THANKS: 謝謝
    if any(kw in combined for kw in ["謝謝", "谢谢", "感謝", "感谢", "thank"]):
        events.append(("THANKS", "MEDIUM"))
    
    # JOKE: 笑、有趣
    if any(kw in combined for kw in ["哈哈", "笑死", "好笑", "有趣", "lol", "哈哈", "😂", "🤣"]):
        events.append(("JOKE", "MEDIUM"))
    
    # LONG_CHAT: 對話長度判斷
    # LOW: 50-150 字
    # MEDIUM: 150-300 字
    # HIGH: 300+ 字
    total_len = len(user_msg) + len(lin_reply)
    if total_len > 300:
        events.append(("LONG_CHAT", "HIGH"))
    elif total_len > 150:
        events.append(("LONG_CHAT", "MEDIUM"))
    elif total_len > 50:
        events.append(("LONG_CHAT", "LOW"))
    
    # SHORT_REPLY: Lin 回覆很短且 user 訊息不短
    if len(lin_reply) < 10 and len(user_msg) > 15:
        events.append(("SHORT_REPLY", "MEDIUM"))
    
    # LATE_NIGHT: 現在是深夜（23:00~05:00）
    # 強度根據時間深淺判斷：
    # LOW: 23:00-00:00 或 04:00-05:00 (剛入夜或接近天亮)
    # MEDIUM: 00:00-01:00 或 03:00-04:00
    # HIGH: 01:00-03:00 (深夜核心時段)
    hour = datetime.now().hour
    if 1 <= hour < 3:
        events.append(("LATE_NIGHT", "HIGH"))
    elif (0 <= hour < 1) or (3 <= hour < 4):
        events.append(("LATE_NIGHT", "MEDIUM"))
    elif (23 <= hour < 24) or (4 <= hour < 5):
        events.append(("LATE_NIGHT", "LOW"))
    
    return events

def generate_reply(context, app_name=None, use_cache=True):
    """
    返回 (reply_text, thinking_text)。
    thinking_text 是清理过、可以直接显示给Anna看的思考内容；命中缓存或没配置API key时是 None。
    """
    # V1 新增：對話前先 tick 身體狀態
    from datetime import datetime
    from app.intimacy.tick import tick_and_update
    from app.intimacy.event import check_event_triggers
    from app.intimacy.silence import detect_silence
    
    now = datetime.now()
    tick_and_update(state, now)
    
    # V2 新增：更新用戶最後發消息時間，重置連續對話計數
    if not hasattr(state, 'last_user_message_at'):
        state.last_user_message_at = now
    else:
        # 檢查是否是連續對話（間隔少於 10 分鐘）
        if state.last_user_message_at:
            gap_minutes = (now - state.last_user_message_at).total_seconds() / 60.0
            if gap_minutes < 10:
                state.continuous_turns = getattr(state, 'continuous_turns', 0) + 1
            else:
                state.continuous_turns = 1
        else:
            state.continuous_turns = 1
    
    state.last_user_message_at = now
    
    # V2 新增：檢查是否該觸發事件
    from app.intimacy.tick import start_event
    
    # 檢測等待焦躁（如果之前有等待）
    silence_info = detect_silence(state.last_user_message_at, now) if hasattr(state, 'last_user_message_at') else {}
    
    # 組裝觸發情境
    trigger_context = {
        "silence_minutes": silence_info.get("silence_minutes", 0),
        "continuous_turns": getattr(state, 'continuous_turns', 0)
    }
    
    # 檢查所有觸發條件
    triggered_events = check_event_triggers(state.body_values, trigger_context)
    
    # 如果有觸發且目前沒有事件，啟動第一個觸發的事件
    if triggered_events and not getattr(state, 'active_event_key', None):
        start_event(state, triggered_events[0], now)
    
    if use_cache and state.last_context_cache == context and state.last_reply_at:
        if datetime.now() - state.last_reply_at < timedelta(minutes=2):
            return random.choice(FALLBACK_REPLIES), None

    if not state.check_rate_limit():
        return "今天额度用完了，或者刚刚问太快了，等一下再说。", None

    memory_summary = state.recent_memory_text()
    memory_summary = state.recent_memory_text()
    conv_list = state.get_recent_conversation(n=20)
    if conv_list:
        formatted = []
        for item in conv_list:
            if item["role"] == "user":
                formatted.append(f"Anna: {item['content']}")
            else:
                formatted.append(f"Lin: {item['content']}")
        conversation_history = "\n".join(formatted)
    else:
        conversation_history = "(无最近对话)"

    persona = Persona.get_system_prompt()
    final_system = f"{persona}\n\n{memory_summary}\n\n最近对话：\n{conversation_history}"

    messages = [
        {"role": "system", "content": final_system},
        {"role": "user", "content": context}
    ]

    reply, thinking = llm.chat(messages, use_thinking=LLM_THINKING_ENABLED)
    
    # V3 新增：對話結束後結算關係
    if reply and hasattr(state, 'relationship'):
        from app.intimacy.settlement import settle_interaction
        state.relationship = settle_interaction(
            state.relationship,
            context,
            reply,
            getattr(state, 'continuous_turns', 1)
        )
    
    # V3 新增：檢測是否該觸發主事件（親密釋放）
    from app.intimacy.ephemeral import should_trigger_intimacy_release, trigger_ephemeral_event
    
    if should_trigger_intimacy_release(context, reply, state.body_values):
        trigger_ephemeral_event(state, "intimacy_release", now)

    state.last_reply_at = datetime.now()
    state.last_context_cache = context
    return reply, thinking
    if conv_list:
        formatted = []
        for turn in conv_list:
            role_name = "Anna" if turn["role"] == "anna" else "Lin"
            formatted.append(f"{role_name}：{turn['content']}")
        conversation_history = "\n".join(formatted)
    else:
        conversation_history = ""
    
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

        mood_event = parse_mood_event(reasoning)
        if mood_event:
            events = mood_event["events"]
            line = mood_event.get("line")
            for i, (event_name, event_level) in enumerate(events):
                # line 只在最后一次调用时写入，避免中间事件把 line 覆盖成空/重复
                mood_engine.apply_event(
                    event_name, 
                    level=event_level,
                    line=line if i == len(events) - 1 else None
                )

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

def generate_reply_stream(context, app_name=None, use_cache=True, session_id=None):
    """
    流式生成回覆，yield SSE 格式的事件。
    """
    from app.llm.deepseek_client import call_deepseek_stream
    from app.memory_rules import parse_memory_decision, parse_mood_event, strip_hidden_blocks
    from app import mood_engine
    
    target_session = session_id or state.current_session_id
    
    if not state.check_rate_limit():
        err_msg = "今天额度用完了，或者刚刚问太快了，ata: {}\n\n"
        return
    
    if use_cache and state.last_context_cache == context and state.last_reply_at:
        if datetime.now() - state.last_reply_at < timedelta(minutes=2):
            yield f"data: {json.dumps({'type': 'content', 'text': random.choice(FALLBACK_REPLIES)})}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"
            return
    
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
    
    world_context = format_context_for_prompt(get_context())
    system_prompt = build_system_prompt(context, memory_summary, world_context, conversation_history)
    
    state.record_call()
    
    full_reasoning = ""
    raw_reasoning = ""
    full_content = ""
    
    try:
        for event_type, data in call_deepseek_stream(system_prompt, max_tokens=config.DEEPSEEK_MAX_TOKENS):
            if event_type == "reasoning":
                full_reasoning += data
                yield f"event: reasoning\ndata: {json.dumps({'content': data})}\n\n"
            elif event_type == "content":
                full_content += data
                yield f"event: content\ndata: {json.dumps({'delta': data})}\n\n"
            elif event_type == "raw_reasoning":
                raw_reasoning = data
            elif event_type == "error":
                state.add_log("AI回复", f"API失败：{data}")
                yield 'event: content\ndata: ' + json.dumps({'delta': '信号不好。'}) + '\n\n'
                yield "event: done\ndata: {}\n\n"
                return
            elif event_type == "done":
                parse_source = raw_reasoning or full_reasoning
                if parse_source:
                    decision = parse_memory_decision(parse_source)
                    if decision:
                        state.remember_or_reinforce(decision)
                
                # Auto-detect mood events from user + Lin content
                detected_events = _auto_detect_mood_events(context, full_content)
                for event_name, event_level in detected_events:
                    mood_engine.apply_event(event_name, level=event_level)
                
                state.last_context_cache = context
                state.mark_reply()
                state.add_log("AI回复", f"成功：{full_content[:40]}...")
                
                if full_content and full_content not in ("信号不好。", "今天额度用完了，或者刚刚问太快了，等一下再说。"):
                    thinking_display = strip_hidden_blocks(full_reasoning) if full_reasoning else None
                    state.add_conversation_turn("lin", full_content, thinking=thinking_display, session_id=target_session)
                    
                    from app.notify.bark import send_to_bark
                    send_to_bark(full_content)
                
                state.mark_conversation_anchor()
                yield "event: done\ndata: {}\n\n"
    
    except Exception as e:
        state.add_log("AI回复", f"失败：{str(e)}")
        fallback_payload = json.dumps({'delta': '信号不好。'})
        yield "event: content\ndata: " + fallback_payload + "\n\n"
        yield "event: done\ndata: {}\n\n"
