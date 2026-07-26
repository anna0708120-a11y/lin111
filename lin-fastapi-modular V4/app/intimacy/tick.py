"""
時間推進系統（V1）

讓身體狀態隨時間自動變化
"""

from datetime import datetime, timedelta
from typing import Optional


def tick_and_update(state, now: datetime):
    """
    主要入口：推進時間並更新狀態
    
    Args:
        state: 全局狀態對象
        now: 當前時間
    """
    from app.intimacy.cycle import advance_cycle, get_current_cycle
    from app.intimacy.body_state import calculate_body_state
    
    # 初始化（第一次使用）
    if not hasattr(state, 'last_tick_at') or state.last_tick_at is None:
        from app.intimacy.cycle import enter_cycle
        enter_cycle(state, 'stable', now)
        state.last_tick_at = now
        state.body_values = {"tension": 20, "heat": 30, "sensitivity": 25, "control": 80}
        return
    
    # 計算時間差
    last_tick = state.last_tick_at
    if now <= last_tick:
        return  # 時間沒有前進，不更新
    
    total_elapsed = (now - last_tick).total_seconds() / 3600.0  # 轉成小時
    
    # 分段推進（借鑒 Eventide，每段最多 6 小時）
    MAX_SEGMENT_HOURS = 6.0
    MAX_SEGMENTS = 48
    
    cursor = last_tick
    segments = 0
    
    while cursor < now and segments < MAX_SEGMENTS:
        # 檢查周期是否過期
        advance_cycle(state, cursor)
        
        # 計算本段結束時間
        segment_end = min(now, cursor + timedelta(hours=MAX_SEGMENT_HOURS))
        
        # 如果周期會在本段中過期，提前切到周期過期時間
        if hasattr(state, 'cycle_expires_at') and state.cycle_expires_at:
            if cursor < state.cycle_expires_at < segment_end:
                segment_end = state.cycle_expires_at
        
        # 計算本段經過的小時數
        elapsed_hours = (segment_end - cursor).total_seconds() / 3600.0
        
        if elapsed_hours > 0:
            # 取得當前周期
            cycle = get_current_cycle(state)
            
            # 計算身體狀態變化
            state.body_values = calculate_body_state(
                mood=state.mood,
                cycle=cycle,
                body_values=state.body_values,
                elapsed_hours=elapsed_hours
            )
        
        # 移動游標
        cursor = segment_end
        segments += 1
    
    # 更新最後 tick 時間
    state.last_tick_at = now
