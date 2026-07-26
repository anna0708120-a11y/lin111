"""
定時任務調度器（V4）

讓身體狀態 24 小時自動演化，不需要用戶發消息才更新
"""

import asyncio
from datetime import datetime
from typing import Optional


_scheduler_task: Optional[asyncio.Task] = None


async def tick_loop(state, interval_minutes: int = 10):
    """
    定時 tick 循環
    
    Args:
        state: 全局狀態對象
        interval_minutes: tick 間隔（分鐘）
    """
    from app.intimacy.tick import tick_and_update
    from app.intimacy.dream import maybe_create_dream_trigger
    
    while True:
        try:
            now = datetime.now()
            
            # 1. 推進身體狀態
            tick_and_update(state, now)
            
            # 2. 檢查是否應該生成夢境
            last_message_at = getattr(state, 'last_anchor_at', None)
            if maybe_create_dream_trigger(state, now, last_message_at):
                # 夢境觸發成功，可以記錄日誌
                state.add_log("dream", f"夢境觸發：{getattr(state, 'last_dream_seed', None)}")
            
            # 3. 等待下一次 tick
            await asyncio.sleep(interval_minutes * 60)
            
        except asyncio.CancelledError:
            # 正常關閉
            break
        except Exception as e:
            # 記錄錯誤但不中斷循環
            print(f"Scheduler tick error: {e}")
            await asyncio.sleep(60)  # 發生錯誤時等待 1 分鐘再重試


def start_tick_scheduler(state, interval_minutes: int = 10):
    """
    啟動定時任務
    
    Args:
        state: 全局狀態對象
        interval_minutes: tick 間隔（分鐘）
    """
    global _scheduler_task
    
    if _scheduler_task is not None:
        return  # 已經啟動過了
    
    loop = asyncio.get_event_loop()
    _scheduler_task = loop.create_task(tick_loop(state, interval_minutes))


def stop_tick_scheduler():
    """停止定時任務"""
    global _scheduler_task
    
    if _scheduler_task is not None:
        _scheduler_task.cancel()
        _scheduler_task = None
