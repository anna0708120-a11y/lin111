"""
Mood 模块

管理情绪状态，包括：
- 自然衰减（decay.py）
- 未来扩展：情绪影响、长期趋势等
"""

from .decay import apply_mood_decay, get_decay_summary, MOOD_BASELINES, MOOD_DECAY_RATES

__all__ = [
    "apply_mood_decay",
    "get_decay_summary",
    "MOOD_BASELINES",
    "MOOD_DECAY_RATES",
]
