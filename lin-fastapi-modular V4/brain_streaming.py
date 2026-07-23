def generate_reply_stream(context, app_name=None, use_cache=True):
    """
    Streaming版本的generate_reply。
    Yields dict chunks: {'token': str} | {'thinking_token': str} | {'error': str} | {'done': True}
    """
    from datetime import datetime, timedelta
    from app import config
    from app.state import state
    from app.llm.provider_factory import get_provider
    from app.persona import build_system_prompt
    from app.memory_rules import parse_memory_decision, parse_mood_report, strip_hidden_blocks
    from app.context.provider import get_context, format_context_for_prompt
    
    if use_cache and state.last_context_cache == context and state.last_reply_at:
        if datetime.now() - state.last_reply_at < timedelta(minutes=2):
            import random
            fallback = random.choice(["还没走远。", "嗯。", "我看着你。"])
            yield {'token': fallback}
            yield {'done': True}
            return
    
    if not state.check_rate_limit():
        msg = "今天额度用完了，或者刚刚问太快了，等一下再说。"
        yield {'token': msg}
        yield {'done': True}
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
    
    provider = get_provider()
    state.record_call()
    
    full_content = []
    full_thinking = []
    
    try:
        for chunk in provider.stream_chat(system_prompt, max_tokens=config.DEEPSEEK_MAX_TOKENS):
            if 'error' in chunk:
                yield {'error': chunk['error']}
                return
            elif 'token' in chunk:
                full_content.append(chunk['token'])
                yield {'token': chunk['token']}
            elif 'thinking_token' in chunk:
                full_thinking.append(chunk['thinking_token'])
                yield {'thinking_token': chunk['thinking_token']}
            elif 'done' in chunk:
                break
    except Exception as e:
        yield {'error': str(e)}
        return
    
    content = ''.join(full_content).strip()
    reasoning = ''.join(full_thinking).strip() if full_thinking else None
    
    if not content:
        yield {'token': '信号不好。'}
        yield {'done': True}
        return
    
    if reasoning:
        decision = parse_memory_decision(reasoning)
        if decision:
            state.remember_or_reinforce(decision)
        
        mood = parse_mood_report(reasoning)
        if mood:
            state.update_mood(mood)
    
    state.last_context_cache = context
    state.mark_reply()
    state.add_log("AI回复", f"成功：{content[:40]}...")
    
    yield {'done': True}
