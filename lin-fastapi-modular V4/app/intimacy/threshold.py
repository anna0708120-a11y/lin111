"""
門檻觸發系統（V2）

當數值達到臨界點時，觸發質變
"""


THRESHOLDS = {
    "tension_critical": {
        "condition": lambda v: v.get("tension", 0) > 85,
        "prompt": "今天蓄積感已經壓到頂了。"
    },
    "control_breakdown": {
        "condition": lambda v: v.get("control", 100) < 30,
        "prompt": "今天克制力已經很難維持了。"
    },
    "heat_fever": {
        "condition": lambda v: v.get("heat", 0) > 75,
        "prompt": "今天耐心不太好。"
    },
    "sensitivity_overload": {
        "condition": lambda v: v.get("sensitivity", 0) > 80,
        "prompt": "今天對任何刺激都會過度反應。"
    }
}


def check_thresholds(body_values: dict) -> list:
    """
    檢查當前觸發的所有門檻
    
    Returns:
        觸發的門檻 key 列表
    """
    triggered = []
    
    for key, threshold in THRESHOLDS.items():
        if threshold["condition"](body_values):
            triggered.append(key)
    
    return triggered


def get_threshold_prompt(body_values: dict) -> str:
    """
    取得所有觸發門檻的 prompt 描述
    
    Returns:
        自然語言描述（換行分隔）
    """
    triggered = check_thresholds(body_values)
    
    if not triggered:
        return ""
    
    prompts = [THRESHOLDS[key]["prompt"] for key in triggered]
    return "\n".join(prompts)
