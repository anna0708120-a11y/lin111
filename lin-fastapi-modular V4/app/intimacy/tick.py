"""
時間推進系統（V1 + V2 + V4.2 + V4.3）

讓身體狀態隨時間自動變化，V2 新增事件疊加與餘波處理，V4.2 新增相互影響，V4.3 新增 Mood 自然衰減
"""

from datetime import datetime, timedelta
from typing import Optional
import random


def tick_and_update(state, now: datetime):
    """
    主要入口：推進時間並更新狀態
    
    V2 新增：
    - 檢查事件是否過期
    - 疊加事件 tick_deltas
    - 疊加餘波 deltas
    - 檢測等待焦躁觸發
    
    V4.2 新增：
    - 應用身體狀態相互影響（influence）
    
    V4.3 新增：
    - 應用 Mood 自然衰減（decay）
    """
    from app.intimacy.cycle import advance_cycle, get_current_cycle
    from app.intimacy.body_state import calculate_body_state
    from app.intimacy.event import get_event
    from app.intimacy.event_log import log_event
    from app.intimacy.after_effect import apply_after_effects, cleanup_expired_effects
    from app.intimacy.silence import detect_silence, calculate_silence_pressure
    from app.intimacy.influence import apply_influence
    from app.mood.decay import apply_mood_decay
    
    # 初始化（第一次使用）
    if not hasattr(state, 'last_tick_at') or state.last_tick_at is None:
        from app.intimacy.cycle import enter_cycle
        enter_cycle(state, 'stable', now)
        state.last_tick_at = now
        state.body_values = {"tension": 20, "heat": 30, "sensitivity": 25, "control": 80}
        # V2 初始化
        if not hasattr(state, 'active_event_key'):
            state.active_event_key = None
            state.active_event_started_at = None
            state.active_event_expires_at = None
            state.active_after_effects = []
        return
    
    # 計算時間差
    last_tick = state.last_tick_at
    if now <= last_tick:
        return  # 時間沒有前進，不更新
    
    # 分段推進（借鑒 Eventide，每段最多 6 小時）
    MAX_SEGMENT_HOURS = 6.0
    MAX_SEGMENTS = 48
    
    cursor = last_tick
    segments = 0
    mood_changed = False
    
    while cursor < now and segments < MAX_SEGMENTS:
        # V2: 檢查事件是否過期
        if state.active_event_key and state.active_event_expires_at:
            if cursor >= state.active_event_expires_at:
                _finish_event(state, cursor)
        
        # 檢查周期是否過期
        advance_cycle(state, cursor)
        
        # 計算本段結束時間
        segment_end = min(now, cursor + timedelta(hours=MAX_SEGMENT_HOURS))
        
        # 如果周期會在本段中過期，提前切到周期過期時間
        if hasattr(state, 'cycle_expires_at') and state.cycle_expires_at:
            if cursor < state.cycle_expires_at < segment_end:
                segment_end = state.cycle_expires_at
        
        # 如果事件會在本段中過期，提前切到事件過期時間
        if state.active_event_expires_at:
            if cursor < state.active_event_expires_at < segment_end:
                segment_end = state.active_event_expires_at
        
        # 計算本段經過的小時數
        elapsed_hours = (segment_end - cursor).total_seconds() / 3600.0
        
        if elapsed_hours > 0:
            # 取得當前周期
            cycle = get_current_cycle(state)
            
            # 計算身體狀態變化（周期基線）
            state.body_values = calculate_body_state(
                mood=state.mood,
                cycle=cycle,
                body_values=state.body_values,
                elapsed_hours=elapsed_hours
            )
            
            # V2: 疊加事件 tick_deltas
            if state.active_event_key:
                event = get_event(state.active_event_key)
                if event:
                    for field, rate in event.tick_deltas.items():
                        state.body_values[field] = state.body_values.get(field, 0) + rate * elapsed_hours
            
            # V2: 疊加餘波 deltas
            if hasattr(state, 'active_after_effects') and state.active_after_effects:
                state.body_values = apply_after_effects(
                    state.body_values,
                    state.active_after_effects,
                    elapsed_hours
                )
            
            # V2: 疊加等待焦躁壓力
            if hasattr(state, 'last_user_message_at') and state.last_user_message_at:
                silence_info = detect_silence(state.last_user_message_at, segment_end)
                silence_deltas = calculate_silence_pressure(silence_info["silence_minutes"])
                for field, delta in silence_deltas.items():
                    state.body_values[field] = state.body_values.get(field, 0) + delta * elapsed_hours
            
            # V4.2: 應用身體狀態相互影響
            state.body_values = apply_influence(state.body_values, enabled=True)
            
            # V4.3: 應用 Mood 自然衰減
            # V4.3: 傳入當前周期，使用動態 target
            cycle = get_current_cycle(state)
            state.mood = apply_mood_decay(state.mood, elapsed_hours, enabled=True, cycle_key=cycle.key)
            mood_changed = True
            
            # clamp 到 0-100
            for key in state.body_values:
                state.body_values[key] = max(0, min(100, state.body_values[key]))
        
        # 移動游標
        cursor = segment_end
        segments += 1
    
    # V2: 清理過期餘波
    if hasattr(state, 'active_after_effects'):
        state.active_after_effects = cleanup_expired_effects(state.active_after_effects, now)

    if mood_changed:
        state.update_mood(state.mood)

    # 更新最後 tick 時間
    state.last_tick_at = now


def start_event(state, event_key: str, now: datetime) -> bool:
    """
    啟動事件
    
    Returns:
        是否成功啟動（如果已有未過期事件則失敗）
    """
    from app.intimacy.event import get_event
    
    # 如果已有未過期事件，不覆蓋
    if state.active_event_key and state.active_event_expires_at:
        if now < state.active_event_expires_at:
            return False
    
    event = get_event(event_key)
    if not event:
        return False
    
    # 隨機抽取持續時間
    min_minutes, max_minutes = event.duration_minutes
    duration_minutes = random.randint(min_minutes, max_minutes)
    
    state.active_event_key = event.key
    state.active_event_started_at = now
    state.active_event_expires_at = now + timedelta(minutes=duration_minutes)
    
    # V4: 寫入事件日誌
    log_event(
        event_type="event",
        title=event.label,
        timestamp=now,
        duration_minutes=duration_minutes,
        metadata={"event_key": event.key}
    )
    
    return True


def _finish_event(state, now: datetime):
    """
    結束事件並施加 end_deltas
    """
    from app.intimacy.event import get_event
    from app.intimacy.after_effect import create_after_effect
    
    if not state.active_event_key:
        return
    
    event = get_event(state.active_event_key)
    if event:
        # 施加 end_deltas
        for field, delta in event.end_deltas.items():
            state.body_values[field] = state.body_values.get(field, 0) + delta
        
        # V2: 創建餘波（如果有對應模板）
        after_effect = create_after_effect(event.key, now)
        if after_effect:
            if not hasattr(state, 'active_after_effects'):
                state.active_after_effects = []
            state.active_after_effects.append(after_effect)
    
    # 清空事件
    state.active_event_key = None
    state.active_event_started_at = None
    state.active_event_expires_at = None

