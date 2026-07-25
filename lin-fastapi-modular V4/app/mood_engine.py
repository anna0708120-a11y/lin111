"""
Mood Engine V2 - Python 負責狀態管理，LLM 只負責演出人格

核心設計：
1. Python 維護所有 mood 數值（0~1）
2. LLM 只判斷「發生了什麼事件」（如 PRAISE、IGNORE）
3. Python 根據事件自動更新數值
4. LLM 讀取當前 mood 數值，自然演出對應的情緒反應
"""

from app.state import state


# Event → 數值變化對照表（集中管理，方便調整）
EVENT_EFFECTS = {
    "PRAISE": {
        "attachment": +0.05,
        "curiosity": +0.03,
        "social": +0.04,
        "stress": -0.05,
    },
    "COMFORT": {
        "attachment": +0.06,
        "possessiveness": +0.02,
        "social": +0.03,
        "stress": -0.03,
    },
    "THANKS": {
        "attachment": +0.03,
        "social": +0.02,
    },
    "PET": {
        "attachment": +0.04,
        "possessiveness": +0.03,
        "social": +0.05,
        "stress": -0.04,
    },
    "POKE": {
        "curiosity": +0.03,
        "social": +0.04,
        "stress": -0.02,
    },
    "JOKE": {
        "social": +0.05,
        "curiosity": +0.02,
        "stress": -0.03,
    },
    "APOLOGY": {
        "attachment": +0.02,
        "stress": -0.06,
    },
    "IGNORE": {
        "attachment": -0.03,
        "possessiveness": +0.02,
        "curiosity": +0.04,
        "stress": +0.03,
    },
    "LONG_IGNORE": {
        "attachment": -0.08,
        "possessiveness": +0.05,
        "curiosity": +0.06,
        "social": -0.04,
        "stress": +0.08,
    },
    "GOODBYE": {
        "curiosity": +0.02,
        "social": -0.02,
    },
    "LONG_CHAT": {
        "attachment": +0.04,
        "social": +0.03,
        "curiosity": +0.02,
        "fatigue": +0.05,
    },
    "SHORT_REPLY": {
        "attachment": -0.02,
        "curiosity": +0.03,
        "social": -0.02,
        "stress": +0.02,
    },
    "LATE_NIGHT": {
        "attachment": +0.03,
        "possessiveness": +0.02,
        "fatigue": +0.06,
        "stress": +0.03,
    },
    "NONE": {
        # 普通對話，數值自然回歸，稍微降低極端值
        "fatigue": -0.01,
        "stress": -0.01,
    },
}


def apply_event(event, line=None):
    """
    應用一個互動事件，自動更新 mood 數值
    
    Args:
        event: 事件名稱（字串），例如 "PRAISE"、"IGNORE"
        line: 可選的心情文字，會更新到 mood.line
    
    範例：
        apply_event("PRAISE")  # attachment 上升，stress 下降
        apply_event("LONG_IGNORE", line="在等妳的消息")
    """
    # 未知事件安全跳過，不報錯
    if event not in EVENT_EFFECTS:
        return
    
    # 取得當前 mood（深拷貝避免直接修改）
    current_mood = state.mood.copy()
    
    # 取得該事件的數值變化規則
    effects = EVENT_EFFECTS[event]
    
    # 應用數值變化
    for key, delta in effects.items():
        if key in current_mood:
            new_value = current_mood[key] + delta
            # 限制在 0.0 ~ 1.0 範圍內（避免溢出）
            current_mood[key] = max(0.0, min(1.0, new_value))
    
    # 更新心情文字（如果提供的話）
    if line:
        current_mood["line"] = line
    
    # 寫回 state（state.update_mood 會同步到 Supabase）
    state.update_mood(current_mood)


def get_current_mood():
    """
    取得當前 mood 狀態（唯讀）
    
    Returns:
        dict: 當前的 mood 數值
    """
    return state.mood.copy()


def format_mood_for_prompt():
    """
    將當前 mood 格式化成適合放進 Prompt 的文字
    
    Returns:
        str: 格式化後的 mood 說明，例如：
             "目前狀態（唯讀，只能閱讀，不能修改）：
              attachment: 0.65
              stress: 0.23
              ..."
    """
    mood = state.mood
    lines = ["目前狀態（唯讀，只能閱讀，不能修改）："]
    
    # 排除 line 欄位，只顯示數值
    for key, value in mood.items():
        if key != "line" and isinstance(value, (int, float)):
            lines.append(f"  {key}: {value:.2f}")
    
    return "\n".join(lines)
