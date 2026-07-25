"""
Mood Engine V2：心情数值由 Python 维护，LLM 只负责判断"这一轮属于哪种事件"，不再自己计算/输出 0-1 数值。

背景：旧版 [MOOD_REPORT] 让模型在 reasoning 里自己吐出六个数值，实测证实模型会因为
STYLE_GUIDE 里"意识流/禁止工具性格式"的规则跟这个结构化格式冲突，直接整段跳过，导致数值永远不变。
改成事件判定后，数值涨跌固定由这里的表控制，LLM 只需要选一个最贴近的事件名，不再需要自己打分。
"""
from app.state import state

# 事件 -> 各数值的增减量。只列出会变动的欄位，没列到的欄位这次不动。
EVENT_DELTAS = {
    "PRAISE":      {"attachment": 0.03, "stress": -0.02},
    "COMFORT":     {"attachment": 0.02, "stress": -0.03, "fatigue": -0.01},
    "THANKS":      {"attachment": 0.01, "social": 0.01},
    "PET":         {"attachment": 0.02},
    "POKE":        {"curiosity": 0.02, "social": 0.01},
    "JOKE":        {"social": 0.02, "stress": -0.01},
    "APOLOGY":     {"stress": -0.02, "possessiveness": -0.01},
    "IGNORE":      {"attachment": -0.02, "stress": 0.02},
    "LONG_IGNORE": {"attachment": -0.04, "stress": 0.05, "possessiveness": 0.02},
    "GOODBYE":     {"social": -0.01},
    "LONG_CHAT":   {"social": 0.02, "fatigue": 0.02},
    "SHORT_REPLY": {"social": -0.01, "curiosity": -0.01},
    "LATE_NIGHT":  {"fatigue": 0.03, "stress": 0.01},
    "NONE":        {},
}

# 这几个欄位才受事件表控制会被 clamp；libido 等其他既有欄位维持原值，不因为改版被吃掉。
MOOD_KEYS = ["attachment", "possessiveness", "curiosity", "social", "fatigue", "stress"]

def apply_event(event_name, line=None):
    """
    根据事件名对 state.mood 做增减，clamp 到 0~1 之后写回 state（state.update_mood 本身就会持久化）。
    event_name 不在表里时视为 NONE（数值不变），line 有给就更新、没给就保留原本的 line。
    回传更新后的完整 mood dict，方便呼叫端或测试直接检查结果。
    """
    deltas = EVENT_DELTAS.get(event_name, EVENT_DELTAS["NONE"])
    current = dict(state.mood) if state.mood else {}

    new_mood = dict(current)
    for key in MOOD_KEYS:
        base = current.get(key, 0.5)
        new_mood[key] = max(0.0, min(1.0, base + deltas.get(key, 0.0)))

    new_mood["line"] = (line or current.get("line") or "在想妳")[:60]

    state.update_mood(new_mood)
    return new_mood
