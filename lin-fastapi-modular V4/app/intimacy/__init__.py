"""
Intimacy Engine 入口（V1-V4.1 完整版）
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

from app.intimacy.consent import (
    calculate_consent,
    get_consent_level,
    get_consent_description
)

from app.intimacy.dream import (
    DreamSeed,
    DreamSettings,
    maybe_create_dream_trigger,
    extract_dream_seed,
    apply_dream_after_effect
)

from app.intimacy.dream_history import (
    DreamHistory,
    DreamRecord
)

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
    'render_consistency_prompt',
    'calculate_consent',
    'get_consent_level',
    'get_consent_description',
    'DreamSeed',
    'DreamSettings',
    'maybe_create_dream_trigger',
    'extract_dream_seed',
    'apply_dream_after_effect',
    'DreamHistory',
    'DreamRecord'
]
