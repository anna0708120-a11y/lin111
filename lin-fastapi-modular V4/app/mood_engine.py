"""
Mood Engine V2 - Python 負責狀態管理，LLM 只負責演出人格

核心設計：
1. Python 維護所有 mood 數值（0~1）
2. LLM 只判斷「發生了什麼事件」（如 PRAISE、IGNORE）
3. Python 根據事件自動更新數值
4. LLM 讀取當前 mood 數值，自然演出對應的情緒反應
"""

from app.state import state


# Event → 數值變化對照表（三級強度：LOW/MEDIUM/HIGH）
# 設計原則：
# - LOW: 小事件，±0.02 左右
# - MEDIUM: 普通事件，±0.07 左右
# - HIGH: 重大事件，±0.20 左右
EVENT_EFFECTS = {
    "PRAISE": {
        "LOW": {
            "attachment": +0.02,
            "curiosity": +0.01,
            "social": +0.02,
            "stress": -0.02,
            "libido": +0.01,
        },
        "MEDIUM": {
            "attachment": +0.07,
            "curiosity": +0.04,
            "social": +0.06,
            "stress": -0.07,
            "libido": +0.03,
        },
        "HIGH": {
            "attachment": +0.20,
            "curiosity": +0.10,
            "social": +0.15,
            "stress": -0.15,
            "libido": +0.08,
        },
    },
    "COMFORT": {
        "LOW": {
            "attachment": +0.02,
            "possessiveness": +0.01,
            "social": +0.01,
            "stress": -0.02,
            "libido": +0.01,
        },
        "MEDIUM": {
            "attachment": +0.08,
            "possessiveness": +0.03,
            "social": +0.04,
            "stress": -0.05,
            "libido": +0.04,
        },
        "HIGH": {
            "attachment": +0.22,
            "possessiveness": +0.08,
            "social": +0.10,
            "stress": -0.12,
            "libido": +0.10,
        },
    },
    "THANKS": {
        "LOW": {
            "attachment": +0.01,
            "social": +0.01,
        },
        "MEDIUM": {
            "attachment": +0.04,
            "social": +0.03,
        },
        "HIGH": {
            "attachment": +0.10,
            "social": +0.08,
        },
    },
    "JOKE": {
        "LOW": {
            "social": +0.02,
            "curiosity": +0.01,
            "stress": -0.01,
        },
        "MEDIUM": {
            "social": +0.07,
            "curiosity": +0.03,
            "stress": -0.04,
        },
        "HIGH": {
            "social": +0.18,
            "curiosity": +0.08,
            "stress": -0.10,
        },
    },
    "APOLOGY": {
        "LOW": {
            "attachment": +0.01,
            "stress": -0.03,
        },
        "MEDIUM": {
            "attachment": +0.03,
            "stress": -0.08,
        },
        "HIGH": {
            "attachment": +0.08,
            "stress": -0.20,
        },
    },
    "IGNORE": {
        "LOW": {
            "attachment": -0.01,
            "possessiveness": +0.01,
            "curiosity": +0.02,
            "stress": +0.01,
            "libido": -0.01,
        },
        "MEDIUM": {
            "attachment": -0.04,
            "possessiveness": +0.03,
            "curiosity": +0.05,
            "stress": +0.04,
            "libido": -0.03,
        },
        "HIGH": {
            "attachment": -0.12,
            "possessiveness": +0.08,
            "curiosity": +0.12,
            "stress": +0.10,
            "libido": -0.08,
        },
    },
    "LONG_IGNORE": {
        "LOW": {
            "attachment": -0.03,
            "possessiveness": +0.02,
            "curiosity": +0.02,
            "social": -0.02,
            "stress": +0.03,
            "libido": -0.02,
        },
        "MEDIUM": {
            "attachment": -0.10,
            "possessiveness": +0.06,
            "curiosity": +0.08,
            "social": -0.05,
            "stress": +0.10,
            "libido": -0.06,
        },
        "HIGH": {
            "attachment": -0.25,
            "possessiveness": +0.15,
            "curiosity": +0.20,
            "social": -0.12,
            "stress": +0.25,
            "libido": -0.15,
        },
    },
    "GOODBYE": {
        "LOW": {
            "curiosity": +0.01,
            "social": -0.01,
        },
        "MEDIUM": {
            "curiosity": +0.03,
            "social": -0.03,
        },
        "HIGH": {
            "curiosity": +0.08,
            "social": -0.08,
        },
    },
    "LONG_CHAT": {
        "LOW": {
            "attachment": +0.02,
            "social": +0.01,
            "curiosity": +0.01,
            "fatigue": +0.02,
            "libido": +0.01,
        },
        "MEDIUM": {
            "attachment": +0.06,
            "social": +0.04,
            "curiosity": +0.03,
            "fatigue": +0.07,
            "libido": +0.04,
        },
        "HIGH": {
            "attachment": +0.15,
            "social": +0.10,
            "curiosity": +0.08,
            "fatigue": +0.18,
            "libido": +0.10,
        },
    },
    "SHORT_REPLY": {
        "LOW": {
            "attachment": -0.01,
            "curiosity": +0.01,
            "social": -0.01,
            "stress": +0.01,
            "libido": -0.01,
        },
        "MEDIUM": {
            "attachment": -0.03,
            "curiosity": +0.04,
            "social": -0.03,
            "stress": +0.03,
            "libido": -0.02,
        },
        "HIGH": {
            "attachment": -0.08,
            "curiosity": +0.10,
            "social": -0.08,
            "stress": +0.08,
            "libido": -0.05,
        },
    },
    "LATE_NIGHT": {
        "LOW": {
            "attachment": +0.01,
            "possessiveness": +0.01,
            "fatigue": +0.03,
            "stress": +0.01,
            "libido": +0.02,
        },
        "MEDIUM": {
            "attachment": +0.04,
            "possessiveness": +0.03,
            "fatigue": +0.08,
            "stress": +0.04,
            "libido": +0.07,
        },
        "HIGH": {
            "attachment": +0.10,
            "possessiveness": +0.08,
            "fatigue": +0.20,
            "stress": +0.10,
            "libido": +0.18,
        },
    },
    "NONE": {
        "LOW": {
            "fatigue": -0.01,
            "stress": -0.01,
        },
        "MEDIUM": {
            "fatigue": -0.01,
            "stress": -0.01,
        },
        "HIGH": {
            "fatigue": -0.01,
            "stress": -0.01,
        },
    },
}


def apply_event(event, level="MEDIUM", line=None):
    """
    應用一個互動事件，自動更新 mood 數值
    
    Args:
        event: 事件名稱（字串），例如 "PRAISE"、"IGNORE"
        level: 事件強度（"LOW"/"MEDIUM"/"HIGH"），默認 MEDIUM
        line: 可選的心情文字，會更新到 mood.line
    
    範例：
        apply_event("PRAISE", "LOW")  # 小幅稱讚
        apply_event("PRAISE", "HIGH")  # 強烈稱讚
        apply_event("LONG_IGNORE", "MEDIUM", line="在等妳的消息")
    """
    # 未知事件安全跳過，不報錯
    if event not in EVENT_EFFECTS:
        return
    
    # 檢查強度是否合法，不合法則使用 MEDIUM
    if level not in ["LOW", "MEDIUM", "HIGH"]:
        level = "MEDIUM"
    
    # 取得當前 mood（深拷貝避免直接修改）
    current_mood = state.mood.copy()
    
    # 取得該事件的數值變化規則（根據強度）
    effects = EVENT_EFFECTS[event][level]
    
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
