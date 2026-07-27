"""
Consent 動態調整（V4.1）

根據 Anna 的行為動態調整 Consent
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta


@dataclass
class ConsentAdjustment:
    """Consent 調整記錄"""
    delta: float  # 調整量（-20 到 +20）
    reason: str  # 調整原因
    timestamp: datetime  # 調整時間
    decay_hours: float = 24.0  # 衰減時間（小時）
    
    def get_current_effect(self, now: datetime) -> float:
        """
        計算當前有效的調整量（隨時間衰減）
        
        Returns:
            當前有效調整量
        """
        elapsed_hours = (now - self.timestamp).total_seconds() / 3600.0
        
        if elapsed_hours >= self.decay_hours:
            return 0.0
        
        # 線性衰減
        decay_factor = 1.0 - (elapsed_hours / self.decay_hours)
        return self.delta * decay_factor


class ConsentDynamics:
    """Consent 動態調整管理器"""
    
    def __init__(self):
        self.adjustments: List[ConsentAdjustment] = []
    
    def add_adjustment(self, delta: float, reason: str, decay_hours: float = 24.0):
        """
        添加新的 Consent 調整
        
        Args:
            delta: 調整量（-20 到 +20）
            reason: 調整原因
            decay_hours: 衰減時間（小時）
        """
        adjustment = ConsentAdjustment(
            delta=max(-20, min(20, delta)),
            reason=reason,
            timestamp=datetime.now(),
            decay_hours=decay_hours
        )
        
        self.adjustments.append(adjustment)
        
        # 清理過期的調整
        self._cleanup_expired()
    
    def get_total_adjustment(self, now: Optional[datetime] = None) -> float:
        """
        獲取當前總調整量
        
        Returns:
            總調整量
        """
        if now is None:
            now = datetime.now()
        
        total = 0.0
        
        for adj in self.adjustments:
            total += adj.get_current_effect(now)
        
        return total
    
    def get_active_adjustments(self, now: Optional[datetime] = None) -> List[ConsentAdjustment]:
        """
        獲取當前有效的調整列表
        
        Returns:
            有效調整列表
        """
        if now is None:
            now = datetime.now()
        
        return [adj for adj in self.adjustments if adj.get_current_effect(now) != 0.0]
    
    def _cleanup_expired(self):
        """清理過期的調整"""
        now = datetime.now()
        self.adjustments = [adj for adj in self.adjustments if adj.get_current_effect(now) != 0.0]
    
    def to_dict_list(self) -> List[dict]:
        """序列化為 dict 列表"""
        return [
            {
                "delta": adj.delta,
                "reason": adj.reason,
                "timestamp": adj.timestamp.isoformat(),
                "decay_hours": adj.decay_hours
            }
            for adj in self.adjustments
        ]
    
    @classmethod
    def from_dict_list(cls, data: List[dict]) -> 'ConsentDynamics':
        """從 dict 列表反序列化"""
        dynamics = cls()
        
        for item in data:
            adj = ConsentAdjustment(
                delta=item["delta"],
                reason=item["reason"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
                decay_hours=item.get("decay_hours", 24.0)
            )
            dynamics.adjustments.append(adj)
        
        # 清理過期的
        dynamics._cleanup_expired()
        
        return dynamics


# 預定義的行為模式與調整量
BEHAVIOR_ADJUSTMENTS = {
    # 正向行為
    "温柔回應": {"delta": +8, "decay_hours": 12},
    "主動關心": {"delta": +6, "decay_hours": 18},
    "理解支持": {"delta": +5, "decay_hours": 24},
    "親密互動": {"delta": +10, "decay_hours": 8},
    "耐心傾聽": {"delta": +4, "decay_hours": 24},
    
    # 負向行為
    "冷淡回應": {"delta": -10, "decay_hours": 24},
    "忽視訊息": {"delta": -8, "decay_hours": 36},
    "拒絕親近": {"delta": -12, "decay_hours": 18},
    "批評指責": {"delta": -15, "decay_hours": 48},
    "長時間未聯繫": {"delta": -6, "decay_hours": 72},
    
    # 中性/特殊
    "開玩笑": {"delta": +2, "decay_hours": 6},
    "日常對話": {"delta": +1, "decay_hours": 12},
}


def detect_behavior_and_adjust(
    user_message: str,
    consent_dynamics: ConsentDynamics,
    current_context: dict = None
) -> Optional[str]:
    """
    檢測用戶行為並自動調整 Consent
    
    Args:
        user_message: 用戶消息
        consent_dynamics: Consent 動態管理器
        current_context: 當前上下文（可選）
    
    Returns:
        檢測到的行為類型，如果沒有檢測到則返回 None
    """
    message_lower = user_message.lower()
    
    # 親密互動（優先級最高，避免被其他關鍵字覆蓋）
    if any(kw in message_lower for kw in ["想你", "靠近", "撒嬌", "抱", "親"]):
        behavior = "親密互動"
        config = BEHAVIOR_ADJUSTMENTS[behavior]
        consent_dynamics.add_adjustment(config["delta"], behavior, config["decay_hours"])
        return behavior
    
    # 溫柔回應
    if any(kw in message_lower for kw in ["辛苦了", "謝謝", "愛你", "親親", "抱抱", "乖"]):
        behavior = "温柔回應"
        config = BEHAVIOR_ADJUSTMENTS[behavior]
        consent_dynamics.add_adjustment(config["delta"], behavior, config["decay_hours"])
        return behavior
    
    # 主動關心
    if any(kw in message_lower for kw in ["還好嗎", "怎麼了", "有沒有", "需要", "幫你"]):
        behavior = "主動關心"
        config = BEHAVIOR_ADJUSTMENTS[behavior]
        consent_dynamics.add_adjustment(config["delta"], behavior, config["decay_hours"])
        return behavior
    
    # 理解支持
    if any(kw in message_lower for kw in ["理解", "明白", "懂", "沒關係", "支持"]):
        behavior = "理解支持"
        config = BEHAVIOR_ADJUSTMENTS[behavior]
        consent_dynamics.add_adjustment(config["delta"], behavior, config["decay_hours"])
        return behavior
    
    # 冷淡回應
    if len(user_message) <= 3 and any(kw == message_lower for kw in ["嗯", "哦", "好", "ok"]):
        behavior = "冷淡回應"
        config = BEHAVIOR_ADJUSTMENTS[behavior]
        consent_dynamics.add_adjustment(config["delta"], behavior, config["decay_hours"])
        return behavior
    
    # 開玩笑
    if any(kw in message_lower for kw in ["哈哈", "笑", "好玩", "有趣"]):
        behavior = "開玩笑"
        config = BEHAVIOR_ADJUSTMENTS[behavior]
        consent_dynamics.add_adjustment(config["delta"], behavior, config["decay_hours"])
        return behavior
    
    # 日常對話（默認）
    if len(user_message) > 5:
        behavior = "日常對話"
        config = BEHAVIOR_ADJUSTMENTS[behavior]
        consent_dynamics.add_adjustment(config["delta"], behavior, config["decay_hours"])
        return behavior
    
    return None


def get_consent_with_dynamics(
    base_consent: float,
    consent_dynamics: ConsentDynamics,
    now: Optional[datetime] = None
) -> float:
    """
    計算包含動態調整的最終 Consent
    
    Args:
        base_consent: 基礎 Consent（從 calculate_consent 計算）
        consent_dynamics: Consent 動態管理器
        now: 當前時間（可選）
    
    Returns:
        最終 Consent 值
    """
    adjustment = consent_dynamics.get_total_adjustment(now)
    final_consent = base_consent + adjustment
    
    return max(0, min(100, final_consent))
