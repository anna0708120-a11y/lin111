"""
V2 身體狀態模組（架構預留，V1 不實作）

職責：
- 維護四個短期狀態：熱度 / 敏感度 / 控制力 / 蓄積感
- 自然恢復（Decay）機制
- 受 Mood / 關係階段 / 當前事件影響

設計原則：
- 所有狀態都會自然恢復到基準值
- 不永久累積
- 不屬於 Mood，不屬於 Memory
"""
from typing import Dict, Optional
from datetime import datetime, timedelta

# V2 身體狀態基準值（自然恢復的目標值）
BASELINE = {
    "heat": 0.3,        # 熱度：基準 30%
    "sensitivity": 0.5,  # 敏感度：基準 50%
    "control": 0.7,     # 控制力：基準 70%
    "tension": 0.0      # 蓄積感：基準 0%（完全消散）
}

# Decay 速率（每 10 分鐘恢復的量）
DECAY_RATE = 0.05

# V2 預留：身體狀態類別
class BodyState:
    """
    V2 身體狀態管理（目前未啟用）。
    
    未來功能：
    - 定時 Decay（每 10 分鐘檢查一次）
    - 受事件影響（例如親密互動 → 熱度上升）
    - 受 Mood 影響（例如壓力高 → 控制力下降更快）
    """
    
    def __init__(self):
        self.heat = BASELINE["heat"]
        self.sensitivity = BASELINE["sensitivity"]
        self.control = BASELINE["control"]
        self.tension = BASELINE["tension"]
        self.last_update = datetime.now()
    
    def decay(self):
        """
        自然恢復：每個狀態逐漸回到基準值。
        """
        now = datetime.now()
        elapsed = (now - self.last_update).total_seconds() / 60  # 分鐘
        decay_steps = int(elapsed / 10)  # 每 10 分鐘一次
        
        if decay_steps > 0:
            for _ in range(decay_steps):
                self.heat = self._move_toward(self.heat, BASELINE["heat"], DECAY_RATE)
                self.sensitivity = self._move_toward(self.sensitivity, BASELINE["sensitivity"], DECAY_RATE)
                self.control = self._move_toward(self.control, BASELINE["control"], DECAY_RATE)
                self.tension = self._move_toward(self.tension, BASELINE["tension"], DECAY_RATE)
            self.last_update = now
    
    def _move_toward(self, current: float, target: float, rate: float) -> float:
        """
        將當前值朝目標值移動固定量。
        """
        if current < target:
            return min(current + rate, target)
        elif current > target:
            return max(current - rate, target)
        return current
    
    def to_dict(self) -> Dict[str, float]:
        """
        轉換為字典格式（供 API 回傳）。
        """
        return {
            "heat": round(self.heat, 2),
            "sensitivity": round(self.sensitivity, 2),
            "control": round(self.control, 2),
            "tension": round(self.tension, 2)
        }


# V2 預留：全域身體狀態實例（V1 不初始化）
_body_state: Optional[BodyState] = None


def get_body_state() -> Optional[Dict[str, float]]:
    """
    獲取當前身體狀態（V2 功能，V1 回傳 None）。
    """
    if _body_state is None:
        return None
    _body_state.decay()  # 每次讀取前先 decay
    return _body_state.to_dict()
