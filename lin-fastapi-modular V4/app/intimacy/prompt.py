"""
Intimacy Prompt 組裝（V1 + V2）

用自然語言描述身體狀態，不顯示數字
V2 新增：事件描述、門檻提示、餘波描述
"""

from datetime import datetime


def build_intimacy_prompt(state, now: datetime) -> str:
    """
    組裝完整的 Intimacy Prompt（自然語言，不顯示數字）
    
    只在身體狀態明顯時才顯示相關區塊
    """
    from app.intimacy.cycle import get_current_cycle, get_cycle_progress
    from app.intimacy.consistency import render_consistency_prompt
    from app.intimacy.threshold import get_threshold_prompt
    from app.intimacy.event import get_event
    
    sections = []
    
    # 取得當前數值
    body_values = getattr(state, 'body_values', {})
    if not body_values:
        return ""  # 還沒初始化，不顯示
    
    tension = body_values.get("tension", 20)
    heat = body_values.get("heat", 30)
    sensitivity = body_values.get("sensitivity", 25)
    control = body_values.get("control", 80)
    
    # 判斷是否需要顯示身體狀態（任一數值明顯偏離中間值）
    should_show = (
        tension > 60 or heat > 60 or sensitivity > 60 or control < 50
    )
    
    if not should_show:
        return ""  # 身體狀態不明顯，不顯示
    
    # 1. 身體狀態（自然語言描述）
    body_lines = render_body_state_natural(body_values)
    if body_lines:
        sections.append(f"【身體狀態】\n{body_lines}")
    
    # 2. V2: 門檻觸發
    threshold_prompt = get_threshold_prompt(body_values)
    if threshold_prompt:
        sections.append(f"【門檻觸發】\n{threshold_prompt}")
    
    # 3. 身心一致性
    consistency = render_consistency_prompt(state.mood, body_values)
    if consistency:
        sections.append(f"【身心一致性】\n{consistency}")
    
    # 4. V2: 當前事件
    if hasattr(state, 'active_event_key') and state.active_event_key:
        event = get_event(state.active_event_key)
        if event and state.active_event_expires_at:
            remaining_minutes = (state.active_event_expires_at - now).total_seconds() / 60.0
            sections.append(
                f"【當前事件】\n"
                f"{event.label}（預計還剩 {int(remaining_minutes)} 分鐘）\n"
                f"{event.prompt}"
            )
    
    # 5. V2: 事件餘波
    if hasattr(state, 'active_after_effects') and state.active_after_effects:
        after_effect_lines = []
        for effect in state.active_after_effects:
            remaining_minutes = (effect.expires_at - now).total_seconds() / 60.0
            if remaining_minutes > 0:
                after_effect_lines.append(f"{effect.description}（還剩 {int(remaining_minutes)} 分鐘）")
        
        if after_effect_lines:
            sections.append(f"【事件餘波】\n" + "\n".join(after_effect_lines))
    
    # 6. 周期資訊（僅在非平穩期時顯示）
    cycle = get_current_cycle(state)
    if cycle.key != "stable":
        progress = get_cycle_progress(state, now)
        hours_elapsed = (now - state.cycle_started_at).total_seconds() / 3600.0
        sections.append(f"【周期】\n目前處於{cycle.label}（已持續約 {int(hours_elapsed)} 小時）")
    
    return "\n\n".join(sections)


def render_body_state_natural(body_values: dict) -> str:
    """
    將身體數值轉成自然語言描述（不顯示數字）
    """
    lines = []
    
    tension = body_values.get("tension", 20)
    heat = body_values.get("heat", 30)
    sensitivity = body_values.get("sensitivity", 25)
    control = body_values.get("control", 80)
    
    # heat（熱度）
    if heat > 80:
        lines.append("身體明顯比平時更容易發熱。")
    elif heat > 60:
        lines.append("今天明顯比平時更容易產生身體反應。")
    elif heat > 40:
        lines.append("身體有一點熱意，但還能很快收住。")
    
    # control（控制力）
    if control < 30:
        lines.append("克制力已經很難維持了。")
    elif control < 50:
        lines.append("雖然還能控制自己，但克制已經不像前幾天那麼輕鬆。")
    elif control < 70:
        lines.append("還能維持表面正常，但需要刻意壓著直接的衝動。")
    
    # sensitivity（敏感度）
    if sensitivity > 80:
        lines.append("對任何刺激都會過度反應。")
    elif sensitivity > 60:
        lines.append("偶爾會因為一句話或者一個動作走神。")
    elif sensitivity > 40:
        lines.append("比平時更容易被稱呼、聲音或靠近牽動。")
    
    # tension（蓄積感）
    if tension > 80:
        lines.append("蓄積感已經壓到頂了，隨時可能爆發。")
    elif tension > 60:
        lines.append("身體餘量積著，沒有真的消下去。")
    
    # 通用結尾
    if lines:
        lines.append("")
        lines.append("這些感覺沒有必要主動告訴 Anna，除非互動真的觸碰到了它們。")
    
    return "\n".join(lines)
