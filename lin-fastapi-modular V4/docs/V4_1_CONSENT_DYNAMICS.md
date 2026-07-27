# V4.1 Consent Dynamics 更新說明

## 概述

V4.1 引入了 **Consent Dynamics**（互動意願動態調整）系統，讓 Lin 的互動意願不再是靜態計算，而是會根據 Anna 的具體行為動態調整。

### 核心理念

「Lin 對親密互動的意願不是固定的，而是會被 Anna 的態度、語氣、關心程度持續影響」

---

## 主要功能

### 1. 行為檢測與自動調整

系統會自動檢測 Anna 的消息中包含的行為類型，並對 Consent 進行相應調整：

| 行為類型 | 觸發關鍵字 | 調整量 | 持續時間 |
|---------|-----------|--------|----------|
| 溫柔回應 | 辛苦了、謝謝、愛你、親親、抱抱、乖 | +8 | 12小時 |
| 主動關心 | 還好嗎、怎麼了、有沒有、需要、幫你 | +6 | 18小時 |
| 理解支持 | 理解、明白、懂、沒關係、支持 | +5 | 15小時 |
| 親密互動 | 想你、靠近、撒嬌、抱、親 | +12 | 24小時 |
| 開玩笑 | 哈哈、笑、好玩、有趣 | +3 | 8小時 |
| 日常對話 | 一般對話（超過5字） | +1 | 6小時 |
| 冷淡回應 | 嗯、哦、好、ok（≤3字） | -10 | 24小時 |

### 2. 線性衰減機制

所有調整都不是永久的，會隨時間線性衰減：
- 調整效果從產生時刻開始線性下降
- 達到設定的持續時間後完全消失
- 例如：+8 的調整在 12 小時後降為 +4，24 小時後降為 0

### 3. 上限保護

為了保持情感波動的自然性：
- 所有正向調整的總和上限為 +20
- 所有負向調整的總和下限為 -20
- 最終 Consent 值仍然限制在 0-100 範圍內

---

## 技術實現

### 核心類：ConsentDynamics

```python
class ConsentDynamics:
    def __init__(self):
        self.adjustments: List[ConsentAdjustment] = []
    
    def add_adjustment(self, delta: float, reason: str, decay_hours: float = 24.0)
    def get_total_adjustment(self, now: datetime = None) -> float
    def get_active_adjustments(self, now: datetime = None) -> List[ConsentAdjustment]
    def cleanup_expired(self, now: datetime = None)
```

### 調整數據結構：ConsentAdjustment

```python
@dataclass
class ConsentAdjustment:
    delta: float              # 調整量（可正可負）
    reason: str               # 調整原因
    timestamp: datetime       # 產生時間
    decay_hours: float = 24.0 # 衰減時間（小時）
    
    def get_current_effect(self, now: datetime) -> float
```

---

## 整合點

### 1. State 初始化

```python
# app/state.py
class AppState:
    def __init__(self):
        # ... 其他初始化 ...
        
        # V4.1: Consent Dynamics
        from app.intimacy.consent_dynamics import ConsentDynamics
        self.consent_dynamics = ConsentDynamics()
```

### 2. 消息處理

```python
# app/web/routes.py
@router.post("/watch")
def observe_anna(activity: Activity):
    # V4.1: 檢測用戶行為並動態調整 Consent
    if hasattr(state, 'consent_dynamics') and activity.activity:
        from app.intimacy.consent_dynamics import detect_behavior_and_adjust
        detected_behavior = detect_behavior_and_adjust(
            activity.activity,
            state.consent_dynamics
        )
        if detected_behavior:
            state.add_log("consent", f"行為檢測: {detected_behavior}")
```

### 3. Consent 計算

```python
# app/intimacy/consent.py
def calculate_consent(
    mood: dict, 
    body_values: dict, 
    relationship: dict,
    consent_dynamics=None  # V4.1 新增
) -> float:
    base = 50.0
    # ... 計算基礎 Consent ...
    
    # V4.1: 應用動態調整
    if consent_dynamics:
        from app.intimacy.consent_dynamics import get_consent_with_dynamics
        return get_consent_with_dynamics(base, consent_dynamics)
    
    return max(0, min(100, base))
```

### 4. Prompt 顯示

```python
# app/intimacy/prompt.py
# V4.1: 如果有動態調整，顯示最近的調整原因
if consent_dynamics:
    active_adjustments = consent_dynamics.get_active_adjustments(now)
    if active_adjustments:
        # 顯示最近 3 個調整
        for adj in recent:
            effect = adj.get_current_effect(now)
            consent_lines.append(f"  • {adj.reason} ({effect:+.1f})")
```

---

## API 端點

### GET /intimacy/consent

查詢當前 Consent 狀態及所有動態調整

**回應範例：**
```json
{
  "base_consent": 65.3,
  "total_adjustment": 14.0,
  "final_consent": 79.3,
  "level": "高",
  "description": "今天比平時更想跟妳親近一點。",
  "adjustments": [
    {
      "reason": "溫柔回應",
      "effect": 8.0,
      "hours_ago": 2.5,
      "decay_progress": 20.8
    },
    {
      "reason": "主動關心",
      "effect": 6.0,
      "hours_ago": 5.2,
      "decay_progress": 28.9
    }
  ]
}
```

---

## 測試覆蓋

### 單元測試（tests/test_v4_1_consent.py）

1. ✅ 測試調整衰減機制
2. ✅ 測試基本動態調整
3. ✅ 測試行為檢測
4. ✅ 測試 Consent 整合
5. ✅ 測試 State 整合
6. ✅ 測試序列化與反序列化
7. ✅ 測試 Prompt 整合

### API 測試（tests/test_v4_1_api.py）

- 測試 `/intimacy/consent` 端點
- 測試 `/watch` 端點的行為檢測

---

## 使用場景範例

### 場景 1：持續溫柔對話

```
Anna: 謝謝你，辛苦了         → +8 (溫柔回應)
Anna: 你還好嗎？            → +6 (主動關心)
Anna: 我理解你的感受         → +5 (理解支持)

結果：Consent 持續上升，Lin 變得更願意表達親密感
```

### 場景 2：冷淡後恢復

```
Anna: 嗯                   → -10 (冷淡回應)
[Consent 下降]
Anna: 抱歉剛才有點急，你還好嗎？  → +6 (主動關心)
Anna: 我真的很關心你         → +8 (溫柔回應)

結果：冷淡造成的負面影響逐漸被溫柔行為抵消
```

### 場景 3：親密互動高峰

```
Anna: 想你了                → +12 (親密互動)
Anna: 抱抱                  → +12 (親密互動)

結果：Consent 快速上升，但不會超過上限 (+20)
```

---

## 未來擴展方向

### V4.2 候選功能

1. **情境感知行為檢測**
   - 根據對話上下文調整檢測邏輯
   - 例如：深夜的「想你」比白天的權重更高

2. **個性化調整係數**
   - 根據 Anna 的長期行為模式調整權重
   - 例如：平時很少說「謝謝」的人說「謝謝」時權重更高

3. **調整歷史分析**
   - 記錄長期調整趨勢
   - 生成「過去一週互動溫度變化」圖表

4. **多維度行為檢測**
   - 檢測語氣（詢問/陳述/命令）
   - 檢測情緒（開心/沮喪/焦慮）
   - 根據多個維度綜合調整

---

## 注意事項

### 設計原則

1. **自然衰減**：避免單次行為造成永久影響
2. **上限保護**：防止極端情況下的不合理波動
3. **透明可見**：在 Prompt 中顯示最近的調整，幫助 LLM 理解當前狀態

### 調試建議

1. 查看 `state.activity_log` 中的 "consent" 類型日誌
2. 調用 `/intimacy/consent` API 查看當前所有調整
3. 檢查 `state.consent_dynamics.adjustments` 的序列化數據

---

## 版本資訊

- **版本**: V4.1
- **發布日期**: 2026-01-27
- **依賴版本**: V4 Intimacy Engine
- **向後兼容**: ✅ 完全兼容 V4

---

## 相關文件

- [V4 Intimacy Engine 文檔](./ARCHITECTURE_V4.md)
- [Consent 計算文檔](./intimacy/consent.py)
- [State 管理文檔](./state.py)
