"""
夢境系統（架構預留，不實作完整功能）

預留概念：
- 夢境類型 (dream_type): 例如 "sweet" / "anxious" / "intimate" / "neutral"
- 夢境標籤 (tags): 例如 ["依戀", "佔有", "壓力"]
- 夢後影響 (impact): 對 Mood / Body State 的短期影響幅度

之後可與 Reflection、Memory 聯動：
- 睡眠/離線時段結束後，依近期 Mood + Memory 挑選夢境類型
- 夢後在下一次互動中，短暫調整 Body State 或 Mood 作為「餘韻」

V1 階段不啟用，僅保留資料結構與介面。
"""

class Dream:
    def __init__(self, dream_type="neutral", tags=None, impact=None):
        self.dream_type = dream_type      # "sweet" / "anxious" / "intimate" / "neutral"
        self.tags = tags or []            # 關聯的 Mood/Memory 標籤
        self.impact = impact or {}        # 例如 {"attachment": 0.05, "stress": -0.05}

    def to_dict(self):
        return {
            "dream_type": self.dream_type,
            "tags": self.tags,
            "impact": self.impact,
        }


def generate_dream(mood, memory_snapshot=None):
    """
    V2+ 預留：依 Mood + Memory 生成一個夢境物件。
    V1 階段不啟用，回傳 None。
    """
    return None
