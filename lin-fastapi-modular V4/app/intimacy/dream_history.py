"""
夢境歷史記錄（V4.1）

保存最近 N 個夢境，讓 Lin 可以在對話中提及過去的夢
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from collections import deque


@dataclass
class DreamRecord:
    """夢境記錄"""
    seed: 'DreamSeed'  # 夢境種子
    occurred_at: datetime  # 發生時間
    mentioned: bool = False  # 是否已經在對話中提及過
    impact_summary: str = ""  # 對當時狀態的影響摘要
    
    def to_dict(self) -> dict:
        """序列化為 dict（用於存儲）"""
        return {
            "theme": self.seed.theme,
            "intensity": self.seed.intensity,
            "tags": self.seed.tags,
            "occurred_at": self.occurred_at.isoformat(),
            "mentioned": self.mentioned,
            "impact_summary": self.impact_summary
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DreamRecord':
        """從 dict 反序列化"""
        from app.intimacy.dream import DreamSeed
        
        seed = DreamSeed(
            theme=data["theme"],
            intensity=data["intensity"],
            tags=data["tags"]
        )
        
        return cls(
            seed=seed,
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
            mentioned=data.get("mentioned", False),
            impact_summary=data.get("impact_summary", "")
        )


class DreamHistory:
    """夢境歷史管理器"""
    
    def __init__(self, max_records: int = 10):
        """
        Args:
            max_records: 最多保留的夢境記錄數
        """
        self.records: deque[DreamRecord] = deque(maxlen=max_records)
    
    def add_dream(self, seed: 'DreamSeed', occurred_at: datetime, impact_deltas: dict):
        """
        添加新夢境記錄
        
        Args:
            seed: 夢境種子
            occurred_at: 發生時間
            impact_deltas: 對身體狀態的影響（用於生成摘要）
        """
        # 生成影響摘要
        impact_summary = self._generate_impact_summary(impact_deltas)
        
        record = DreamRecord(
            seed=seed,
            occurred_at=occurred_at,
            mentioned=False,
            impact_summary=impact_summary
        )
        
        self.records.append(record)
    
    def get_recent_dreams(self, n: int = 3, only_unmentioned: bool = False) -> List[DreamRecord]:
        """
        獲取最近的 N 個夢境
        
        Args:
            n: 返回數量
            only_unmentioned: 是否只返回未提及過的夢境
        
        Returns:
            夢境記錄列表（從新到舊）
        """
        records = list(self.records)
        records.reverse()  # 從新到舊排序
        
        if only_unmentioned:
            records = [r for r in records if not r.mentioned]
        
        return records[:n]
    
    def mark_as_mentioned(self, occurred_at: datetime):
        """標記某個夢境已被提及"""
        for record in self.records:
            if record.occurred_at == occurred_at:
                record.mentioned = True
                break
    
    def get_dream_summary_for_prompt(self, days: int = 7) -> str:
        """
        生成用於 Prompt 的夢境摘要
        
        Args:
            days: 最近 N 天的夢境
        
        Returns:
            自然語言描述
        """
        from datetime import timedelta
        
        now = datetime.now()
        cutoff = now - timedelta(days=days)
        
        recent = [r for r in self.records if r.occurred_at >= cutoff]
        
        if not recent:
            return ""
        
        lines = []
        lines.append(f"最近 {days} 天你做過 {len(recent)} 個夢：")
        
        for record in list(recent)[-3:]:  # 最多顯示最近 3 個
            days_ago = (now - record.occurred_at).days
            time_desc = f"{days_ago} 天前" if days_ago > 0 else "今天"
            
            lines.append(f"- {time_desc}：{record.seed.theme}")
            
            if record.mentioned:
                lines.append("  （已經在對話中提過）")
        
        lines.append("")
        lines.append("你可以在適當的時候提及這些夢，但不要刻意強調。")
        
        return "\n".join(lines)
    
    def should_mention_dream(self, current_context: str = "") -> Optional[DreamRecord]:
        """
        判斷是否應該提及某個過去的夢
        
        Args:
            current_context: 當前對話情境
        
        Returns:
            應該提及的夢境記錄，如果不應該提及則返回 None
        """
        import random
        
        # 獲取未提及過的最近 3 個夢境
        unmentioned = self.get_recent_dreams(n=3, only_unmentioned=True)
        
        if not unmentioned:
            return None
        
        # 根據情境相關性計算提及概率
        for record in unmentioned:
            relevance_score = self._calculate_relevance(record, current_context)
            
            # 相關性越高，提及概率越大
            mention_probability = min(0.3, relevance_score * 0.5)
            
            if random.random() < mention_probability:
                return record
        
        return None
    
    def _generate_impact_summary(self, deltas: dict) -> str:
        """生成影響摘要"""
        parts = []
        
        for field, delta in deltas.items():
            if delta > 10:
                parts.append(f"{field}大幅上升")
            elif delta > 5:
                parts.append(f"{field}上升")
            elif delta < -10:
                parts.append(f"{field}大幅下降")
            elif delta < -5:
                parts.append(f"{field}下降")
        
        return "、".join(parts) if parts else "無明顯變化"
    
    def _calculate_relevance(self, record: DreamRecord, current_context: str) -> float:
        """
        計算夢境與當前情境的相關性
        
        Returns:
            相關性分數（0.0-1.0）
        """
        if not current_context:
            return 0.0
        
        score = 0.0
        
        # 檢查主題關鍵字
        theme_keywords = record.seed.theme.lower().split()
        context_lower = current_context.lower()
        
        for keyword in theme_keywords:
            if len(keyword) > 2 and keyword in context_lower:
                score += 0.2
        
        # 檢查標籤相關性
        if "intimate" in record.seed.tags:
            if any(kw in context_lower for kw in ["靠近", "親密", "想你", "抱"]):
                score += 0.3
        
        if "anxious" in record.seed.tags:
            if any(kw in context_lower for kw in ["焦慮", "不安", "擔心", "等"]):
                score += 0.3
        
        if "sweet" in record.seed.tags:
            if any(kw in context_lower for kw in ["溫柔", "陪伴", "散步", "平靜"]):
                score += 0.3
        
        return min(1.0, score)
    
    def to_dict_list(self) -> List[dict]:
        """序列化為 dict 列表（用於存儲）"""
        return [record.to_dict() for record in self.records]
    
    @classmethod
    def from_dict_list(cls, data: List[dict], max_records: int = 10) -> 'DreamHistory':
        """從 dict 列表反序列化"""
        history = cls(max_records=max_records)
        
        for item in data:
            record = DreamRecord.from_dict(item)
            history.records.append(record)
        
        return history
