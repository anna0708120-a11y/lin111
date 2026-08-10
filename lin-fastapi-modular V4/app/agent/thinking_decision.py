"""Two-stage thinking visibility decision."""


def should_show_thinking(context, state, response=None):
    """Return the backend's coarse suggestion for showing thinking text."""
    text = str(context or "")
    response_text = str(response or "")

    complex_markers = (
        "为什么", "為什麼", "原因", "解释", "解釋", "分析", "比较", "比較",
        "怎么做", "怎麼做", "计划", "計劃", "决定", "決定", "推理",
        "reflection", "反思", "memory conflict", "冲突", "衝突",
    )
    if any(marker.lower() in text.lower() for marker in complex_markers):
        return True

    if len(response_text) >= 240:
        return True

    if getattr(state, "continuous_turns", 0) >= 5:
        return True

    if getattr(state, "memory_conflict", False):
        return True
    if getattr(state, "reflection_triggered", False):
        return True

    return False


def parse_model_thinking_decision(reasoning_text):
    """Return the model's explicit yes/no decision, or None if absent."""
    import re

    match = re.search(
        r"\[SHOW_THINKING\]\s*(yes|no)\s*\[/SHOW_THINKING\]",
        reasoning_text or "",
        re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).lower() == "yes"


def clean_thinking_text(reasoning_text):
    """Remove the model-only visibility marker from displayable thinking."""
    import re

    return re.sub(
        r"\[SHOW_THINKING\].*?\[/SHOW_THINKING\]",
        "",
        reasoning_text or "",
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()


def should_emit_thinking(backend_suggestion, reasoning_text):
    """Thinking is visible only when both decisions allow it."""
    return bool(backend_suggestion and parse_model_thinking_decision(reasoning_text) is True)
