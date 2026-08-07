"""
Lin 的"大脑"：把人设(persona) + 记忆(state) + 现实状态(context) + 模型(llm) 串起来，产出一句回复。

不管这轮触发是 Anna 主动发消息、监控到她开了某个 app、
还是 agent/initiative.py 判断"该主动找她了"，最终都走这一个函数。

现在用 DeepSeek 原生 thinking mode：reasoning_content 是真思考，不用再切字符串。
思考内容最后面会藏两段结构化判断（记忆判定、状态自评），处理完之后从"给Anna看的思考内容"里拿掉。
"""
import json
import random
import time
from datetime import datetime, timedelta

from app import config
from app.state import state
from app.llm.deepseek_client import call_deepseek
from app.persona import build_system_prompt
from app.memory_rules import parse_memory_decision, parse_mood_event, strip_hidden_blocks
from app import memory_trace  # Phase 2: 記錄 memory 決策鏈路
from app.context.provider import get_context, format_context_for_prompt
from app import mood_engine
from app.agent.thinking_decision import (
    clean_thinking_text,
    should_emit_thinking,
    should_show_thinking,
)

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
    thinking_suggestion = should_show_thinking(context, state)
    system_prompt = build_system_prompt(
        context,
        memory_summary,
        world_context,
        conversation_history,
        thinking_suggestion=thinking_suggestion,
    )

    content, reasoning = call_deepseek(system_prompt, max_tokens=config.DEEPSEEK_MAX_TOKENS)
    state.record_call()

    if not content:
        return "信号不好。", None

    thinking_display = None
    if reasoning:
        # Phase 2: 開始 trace
        memory_trace.start_trace(session_id=None, message_id=None)
        memory_trace.record_model_output(reasoning_text=reasoning, raw_decision_block=None)
        
        decision = parse_memory_decision(reasoning)
        if decision:
            # 記錄 parse 成功
            memory_trace.record_parse_result(success=True, parsed_decision=decision)
            
            action = decision.get("action", "create")
            result = None
            
            if action == "update":
                result = state.update_memory(decision)
                memory_trace.record_backend_action("update_memory", result)
            elif action == "archive":
                result = state.archive_memory(decision)
                memory_trace.record_backend_action("archive_memory", result)
            else:
                result = state.remember_or_reinforce(decision)
                memory_trace.record_backend_action("remember_or_reinforce", result)
            
            # 記錄 DB 操作結果（假設成功，除非 result 明確失敗）
            if result and result.get("action_taken") != "skipped":
                memory_trace.record_db_result(success=True)
            else:
                memory_trace.record_db_result(success=False, error=result.get("skip_reason") if result else "unknown")
        else:
            # Parse 失敗
            memory_trace.record_parse_result(success=False, error="parse_memory_decision returned None")
        
        # 儲存 trace
        memory_trace.save_trace()

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

        thinking_display = clean_thinking_text(strip_hidden_blocks(reasoning)) or None
        if not should_emit_thinking(thinking_suggestion, reasoning):
            thinking_display = None

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

def _body_state_sse_payload(state):
    """Serialize only the current Body State for the existing SSE client."""
    from app.intimacy.body_state import get_body_level, get_body_description
    values = getattr(state, "body_values", {})
    body_values = {}
    for key in ("tension", "heat", "sensitivity", "control"):
        value = float(values.get(key, 0))
        body_values[key] = {
            "value": round(value, 1),
            "level": get_body_level(value),
            "desc": get_body_description(key, value),
        }
    return {
        "body_values": body_values,
        "cycle_key": getattr(state, "cycle_key", "stable"),
        "active_event_key": getattr(state, "active_event_key", None),
        "updated_at": getattr(state, "last_tick_at", None).isoformat() if getattr(state, "last_tick_at", None) else None,
    }


def generate_reply_stream(context, app_name=None, use_cache=True, session_id=None):
    """Wrap the streaming pipeline so unexpected failures retain their traceback."""
    try:
        yield from _generate_reply_stream_impl(
            context,
            app_name=app_name,
            use_cache=use_cache,
            session_id=session_id,
        )
    except Exception:
        import traceback
        traceback.print_exc()
        raise


def _generate_reply_stream_impl(context, app_name=None, use_cache=True, session_id=None):
    """
    流式生成回覆，yield SSE 格式的事件。
    """
    print("[TRACE-A] enter generate_reply_stream")
    from app.llm.deepseek_client import call_deepseek_stream
    from app.memory_rules import parse_memory_decision, parse_memory_decision_traced, parse_mood_event, strip_hidden_blocks
    from app import mood_engine
    from app.agent.trace_collector import TraceCollector

    collector = TraceCollector()
    target_session = session_id or state.current_session_id

    # Phase 1: SSE 主流程也必须经过与非流式流程相同的 Body State 生命周期。
    # 顺序：先推进旧状态 -> 更新本轮对话上下文 -> 检查 Body 事件 -> 构造 prompt。
    from datetime import datetime
    from app.intimacy.tick import tick_and_update, start_event
    from app.intimacy.event import check_event_triggers
    from app.intimacy.silence import detect_silence

    now = datetime.now()
    tick_and_update(state, now)
    previous_message_at = getattr(state, 'last_user_message_at', None)
    if previous_message_at:
        gap_minutes = (now - previous_message_at).total_seconds() / 60.0
        state.continuous_turns = (getattr(state, 'continuous_turns', 0) + 1) if gap_minutes < 10 else 1
    else:
        state.continuous_turns = 1
    state.last_user_message_at = now

    silence_info = detect_silence(previous_message_at, now) if previous_message_at else {}
    trigger_context = {
        "silence_minutes": silence_info.get("silence_minutes", 0),
        "continuous_turns": getattr(state, "continuous_turns", 0),
    }
    triggered_events = check_event_triggers(state.body_values, trigger_context)
    if triggered_events and not getattr(state, "active_event_key", None):
        start_event(state, triggered_events[0], now)
    if hasattr(state, 'save_body_state'):
        state.save_body_state()
    
    if not state.check_rate_limit():
        err_msg = "今天额度用完了，或者刚刚问太快了，等一下再说。"
        yield f"event: error\ndata: {json.dumps({'message': err_msg})}\n\n"
        yield "event: done\ndata: {}\n\n"
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
    
    print("[TRACE-B] before build context")
    world_context = format_context_for_prompt(get_context())
    print("[TRACE-C] after build context")
    print("[TRACE-D] before build prompt")
    thinking_suggestion = should_show_thinking(context, state)
    system_prompt = build_system_prompt(
        context,
        memory_summary,
        world_context,
        conversation_history,
        thinking_suggestion=thinking_suggestion,
    )
    print("[TRACE-E] after build prompt")

    yield collector.record_prompt(
        "passed",
        prompt_version=getattr(config, "PROMPT_VERSION", None),
        total_tokens=len(system_prompt),
        memory_rule_loaded=True,
        mood_rule_loaded=True,
    )

    state.record_call()
    
    full_reasoning = ""
    raw_reasoning = ""
    full_content = ""
    
    print("[TRACE-H] before call_deepseek")
    try:
        generator = call_deepseek_stream(system_prompt, max_tokens=config.DEEPSEEK_MAX_TOKENS)
        print("[TRACE-I] after call_deepseek")
        for event_type, data in generator:
            print(f"[TRACE] event received: {event_type}")
            if event_type == "reasoning":
                full_reasoning += data
            elif event_type == "content":
                full_content += data
                yield f"event: content\ndata: {json.dumps({'delta': data})}\n\n"
            elif event_type == "raw_reasoning":
                raw_reasoning = data
            elif event_type == "error":
                state.add_log("AI回复", f"API失败：{data}")
                yield 'event: content\ndata: ' + json.dumps({'delta': '信号不好。'}) + '\n\n'
                yield collector.record_reasoning("failed", reasoning_text=None)
                yield "event: done\ndata: {}\n\n"
                return
            elif event_type == "done":
                parse_source = raw_reasoning or full_reasoning
                if should_emit_thinking(thinking_suggestion, parse_source):
                    thinking_display = clean_thinking_text(strip_hidden_blocks(full_reasoning))
                    if thinking_display:
                        yield f"event: reasoning\ndata: {json.dumps({'content': thinking_display})}\n\n"
                yield collector.record_reasoning("passed" if parse_source else "failed", reasoning_text=parse_source)

                if parse_source:
                    print("[TRACE-F] before memory parse")
                    _trace_start = time.time()
                    traced = parse_memory_decision_traced(parse_source)
                    _parse_time_ms = int((time.time() - _trace_start) * 1000)

                    yield collector.record_memory_decision(
                        traced["status"], parsed_decision=traced["decision"], reason=traced["reason"]
                    )
                    yield collector.record_parser(traced["status"], reason=traced["reason"], parse_time_ms=_parse_time_ms)

                    # 正式邏輯仍只用既有的 parse_memory_decision，不依賴 traced 版本的回傳值，
                    # 避免診斷用的包裝函式影響到正式的記憶寫入行為。
                    decision = parse_memory_decision(parse_source)
                    print("[TRACE-G] after memory parse")
                    print(f"[DONE-1] parse_memory_decision 完成, decision={decision is not None}")
                    if decision:
                        action = decision.get("action", "create")
                        if action == "update":
                            _result = state.update_memory(decision)
                            yield collector.record_backend("passed", backend_action="update_memory", action_taken=_result.get("action_taken") if _result else None)
                        elif action == "archive":
                            _result = state.archive_memory(decision)
                            yield collector.record_backend("passed", backend_action="archive_memory", action_taken=_result.get("action_taken") if _result else None)
                        else:
                            _result = state.remember_or_reinforce(decision)
                            yield collector.record_backend("passed", backend_action="remember_or_reinforce", action_taken=_result.get("action_taken") if _result else None)
                        print(f"[DONE-2] 記憶寫入動作完成, action={action}, action_taken={_result.get('action_taken') if _result else None}")

                        if _result and _result.get("memory_id") is not None and _result.get("action_taken") != "skipped":
                            yield collector.record_db("passed", memory_id=_result.get("memory_id"))
                        else:
                            yield collector.record_db("failed", db_error=_result.get("skip_reason") if _result else "handler_failed")
                            yield collector.emit("error", message="記憶寫入失敗")
                    else:
                        yield collector.record_backend("not_executed")
                        yield collector.record_db("not_executed")
                else:
                    yield collector.record_memory_decision("failed", reason="reasoning 為空，無法解析")
                    yield collector.record_parser("failed", reason="reasoning 為空，無法解析")
                    yield collector.record_backend("not_executed")
                    yield collector.record_db("not_executed")

                # Auto-detect mood events from user + Lin content
                detected_events = _auto_detect_mood_events(context, full_content)
                for event_name, event_level in detected_events:
                    mood_engine.apply_event(event_name, level=event_level)
                print(f"[DONE-3] mood_engine.apply_event 完成, detected_events={detected_events}")

                # Phase 1: mood 已写回后，立即执行一次状态同步。
                # tick 本身仍遵守 last_tick_at，避免重复计算或覆盖现有缓存修复。
                tick_and_update(state, datetime.now())

                # mood 更新后再检查一次 Body Event；这样新 mood 不会只能等到下一轮聊天
                # 才参与事件判断。仍遵守 active event 不覆盖规则。
                post_mood_now = datetime.now()
                post_mood_context = {
                    "silence_minutes": 0,
                    "continuous_turns": getattr(state, "continuous_turns", 0),
                }
                post_mood_events = check_event_triggers(state.body_values, post_mood_context)
                if post_mood_events and not getattr(state, "active_event_key", None):
                    start_event(state, post_mood_events[0], post_mood_now)

                if hasattr(state, 'save_body_state'):
                    state.save_body_state()
                yield f"event: body_state\ndata: {json.dumps(_body_state_sse_payload(state), ensure_ascii=False)}\n\n"
                
                state.last_context_cache = context
                state.mark_reply()
                print("[DONE-4] state.mark_reply 完成")
                state.add_log("AI回复", f"成功：{full_content[:40]}...")
                print("[DONE-5] state.add_log 完成")
                
                if full_content and full_content not in ("信号不好。", "今天额度用完了，或者刚刚问太快了，等一下再说。"):
                    thinking_display = strip_hidden_blocks(full_reasoning) if full_reasoning else None
                    state.add_conversation_turn("lin", full_content, thinking=thinking_display, session_id=target_session, trace=collector.export())
                    print("[DONE-6] state.add_conversation_turn 完成")
                    
                    from app.notify.bark import send_to_bark
                    send_to_bark(full_content)
                    print("[DONE-7] send_to_bark 完成")
                
                state.mark_conversation_anchor()
                print("[DONE-8] state.mark_conversation_anchor 完成")
                yield "event: done\ndata: {}\n\n"
    
    except Exception:
        raise
