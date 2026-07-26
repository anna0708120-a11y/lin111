"""
Intimacy Engine 入口（V1）
"""

from app.intimacy.cycle import (
    CYCLES,
    get_current_cycle,
    advance_cycle,
    enter_cycle,
    get_cycle_progress
)

from app.intimacy.body_state import (
    calculate_body_state,
    get_body_level
)

from app.intimacy.tick import tick_and_update

from app.intimacy.prompt import build_intimacy_prompt

from app.intimacy.consistency import render_consistency_prompt

__all__ = [
    'CYCLES',
    'get_current_cycle',
    'advance_cycle', 
    'enter_cycle',
    'get_cycle_progress',
    'calculate_body_state',
    'get_body_level',
    'tick_and_update',
    'build_intimacy_prompt',
    'render_consistency_prompt'
]
