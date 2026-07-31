"""
Mood Engine V2 - Python 負責狀態管理，LLM 只負責演出人格

核心設計：
1. Python 維護所有 mood 數值（0~1）
2. LLM 只判斷「發生了什麼事件」（如 PRAISE、IGNORE）
3. Python 根據事件自動更新數值
4. LLM 讀取當前 mood 數值，自然演出對應的情緒反應
"""

from app.state import state
from collections import deque
from datetime import datetime, timedelta


# V2.1: 事件冷却机制（Phase 2）
# 每个事件独立冷却时间（秒）；同一事件在冷却期内拒绝触发，不打折扣
EVENT_COOLDOWNS = {
    "PRAISE": 600,           # 3 分钟 → 10 分钟
    "COMFORT": 900,          # 4 分钟 → 15 分钟
    "THANKS": 120,           # 2 分钟
    "JOKE": 600,             # 3 分钟 → 10 分钟
    "APOLOGY": 300,          # 5 分钟
    "IGNORE": 600,           # 10 分钟
    "LONG_IGNORE": 1200,     # 20 分钟
    "GOODBYE": 180,          # 3 分钟
    "LONG_CHAT": 1200,       # 5 分钟 → 20 分钟（高频事件，需要更长冷却）
    "SHORT_REPLY": 180,      # 3 分钟
    "LATE_NIGHT": 3600,      # 1 小时（低频事件）
    "NONE": 60,              # 1 分钟
}

# 事件最近触发时间记录：{event_name: last_triggered_datetime}
_event_last_triggered = {}

# V2.2: 單一主事件限制（借鑒 Eventide，防止事件堆疊）
_active_mood_event = None
_active_mood_event_expires_at = None

# 重複事件追蹤（用於遞減效果 - Phase 1 遗留，Phase 2 后弃用）
_recent_events = deque(maxlen=10)
DIMINISHING_MULTIPLIERS = [1.0, 0.7, 0.4, 0.2]
REPEAT_WINDOW_SECONDS = 300


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
    from datetime import datetime, timedelta
    
    # V2.2: 單一主事件檢查（Phase 3）
    # 如果已有未過期的主事件，拒絕新事件（Eventide 風格）
    global _active_mood_event, _active_mood_event_expires_at
    now = datetime.now()
    
    if _active_mood_event and _active_mood_event_expires_at:
        if now < _active_mood_event_expires_at:
            print(f"[mood_engine] 拒絕事件 {event}：主事件 {_active_mood_event} 尚未過期")
            return  # 直接拒絕，不累積
    
    # 未知事件安全跳過，不報錯
    if event not in EVENT_EFFECTS:
        return
    
    # 檢查強度是否合法，不合法則使用 MEDIUM
    if level not in ["LOW", "MEDIUM", "HIGH"]:
        level = "MEDIUM"
    
    # V2.1: 事件冷却檢查（Phase 2）
    # 同一事件在冷却期內直接拒絕觸發，不打折扣、不改動任何數值
    now = datetime.now()
    cooldown_seconds = EVENT_COOLDOWNS.get(event, 0)
    last_triggered = _event_last_triggered.get(event)
    if last_triggered and cooldown_seconds > 0:
        if (now - last_triggered).total_seconds() < cooldown_seconds:
            return  # 冷却中，跳過此次事件
    
    # 記錄這次觸發時間
    _event_last_triggered[event] = now
    
    # V2.2: 啟動主事件鎖定期（10分鐘）
    _active_mood_event = event
    _active_mood_event_expires_at = now + timedelta(minutes=10)
    multiplier = 1.0  # Phase 2: 冷却機制取代遞減係數，通過冷却的事件效果不打折
    
    # 取得當前 mood（深拷貝避免直接修改）
    current_mood = state.mood.copy()
    
    # 取得該事件的數值變化規則（根據強度）
    effects = EVENT_EFFECTS[event][level]
    
    # 應用數值變化（套用遞減係數 + 動態調整）
    for key, delta in effects.items():
        if key in current_mood:
            adjusted_delta = delta * multiplier
            
            # 動態調整：根據當前 mood 值微調效果
            # 規則：越接近極端（0.0 或 1.0），變化幅度越小
            current_value = current_mood[key]
            
            # 針對特定事件和 mood 組合進行動態調整
            dynamic_multiplier = 1.0
            
            # COMFORT 對 stress 的效果：stress 越高，效果越好
            if event in ["COMFORT", "APOLOGY"] and key == "stress" and delta < 0:
                # stress 0.7+ 時效果提升 20%，0.5-0.7 提升 10%
                if current_value >= 0.7:
                    dynamic_multiplier = 1.2
                elif current_value >= 0.5:
                    dynamic_multiplier = 1.1
            
            # PRAISE/THANKS 對 attachment 的效果：attachment 越高，效果越小
            if event in ["PRAISE", "THANKS", "COMFORT"] and key == "attachment" and delta > 0:
                # attachment 0.8+ 時效果降低 30%，0.6-0.8 降低 15%
                if current_value >= 0.8:
                    dynamic_multiplier = 0.7
                elif current_value >= 0.6:
                    dynamic_multiplier = 0.85
            
            # IGNORE/LONG_IGNORE 對 attachment 的效果：attachment 越低，傷害越大
            if event in ["IGNORE", "LONG_IGNORE"] and key == "attachment" and delta < 0:
                # attachment 0.3 以下時傷害加重 20%
                if current_value <= 0.3:
                    dynamic_multiplier = 1.2

            # curiosity/social/libido/fatigue 的正向效果：數值越高，效果越小
            # 補齊原本只套用在 attachment 身上的動態調整，避免這幾個欄位被高頻正向事件持續推滿
            if key in ("curiosity", "social", "libido", "fatigue") and delta > 0:
                if current_value >= 0.8:
                    dynamic_multiplier = 0.7
                elif current_value >= 0.6:
                    dynamic_multiplier = 0.85
            
            # 套用動態係數
            adjusted_delta *= dynamic_multiplier
            
            new_value = current_mood[key] + adjusted_delta
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
