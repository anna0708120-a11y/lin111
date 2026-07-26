# Intimacy Engine V4 完整文檔

## 概述

V4 在 V3 的基礎上新增了兩個核心功能：
1. **互動意願（Consent）**：基於身體、情緒和關係狀態計算當前的互動意願
2. **夢境系統（Dream）**：在離線時段自動生成夢境，影響下次互動的語氣和情緒

---

## 1. 互動意願（Consent）

### 設計理念

互動意願反映「今天 Lin 願不願意靠近、撒嬌、表達情感」。

**計算公式：**
```
consent = 基礎值(50) 
          + 身體因子(tension, heat, sensitivity, control)
          + 情緒因子(attachment, stress, fatigue)
          + 關係因子(safety, rapport)
```

### 數值範圍與行為映射

| Consent 值 | 等級 | 行為特徵 |
|-----------|------|---------|
| 0-30 | 低 | 疲憊、不安、防備，會迴避親密互動 |
| 30-50 | 偏低 | 有點累、有點不確定，保持距離 |
| 50-70 | 中等 | 正常互動，不特別主動也不迴避 |
| 70-85 | 偏高 | 想靠近、會主動撒嬌、更直接 |
| 85-100 | 高 | 強烈想親近、克制力弱、可能會失控 |

### 權重配置

```python
# 身體權重
tension: 0.20    # 蓄積感高 → 更想釋放
heat: 0.15       # 熱度高 → 更容易產生反應
sensitivity: 0.10
control: -0.15   # 控制力低 → 更容易靠近

# 情緒權重
attachment: 20   # 依戀感高 → 更想靠近
stress: -15      # 壓力高 → 想迴避
fatigue: -10     # 疲勞高 → 想休息

# 關係權重
safety: 25       # 安全感高 → 更敢表達
rapport: 15      # 默契好 → 更放鬆
```

### 使用示例

```python
from app.intimacy import calculate_consent, get_consent_description

consent = calculate_consent(state.mood, state.body_values, state.relationship)
# → 85.0

description = get_consent_description(consent, state.mood, state.body_values, state.relationship)
# → "今天很想靠近，而且克制力不太好，可能會更直接一點。"
```

### Prompt 集成

只在 Consent 明顯偏離中間值時顯示：

```
【互動意願】
今天很想靠近，而且克制力不太好，可能會更直接一點。
```

---

## 2. 夢境系統（Dream）

### 設計理念

在 Lin 離線（沒有收到 Anna 消息）超過一定時間後，會自動生成「夢境」，並在下次上線時留下短暫的情緒餘波。

### 夢境數據結構

```python
@dataclass
class DreamSeed:
    theme: str           # 夢境主題（從記憶提取）
    intensity: str       # 強度：low / medium / high
    tags: List[str]      # 標籤：intimate / anxious / sweet / released
```

### 夢境生成流程

#### 2.1 觸發條件

```python
def maybe_create_dream_trigger(state, now, last_message_at) -> bool
```

**必要條件（全部滿足才檢查概率）：**
1. 離線時間 ≥ 3 小時
2. 目前時間在時間窗口內（6:00-9:00 或 22:00-2:00）
3. 距離上次夢境 ≥ 12 小時

**概率計算：**
```
base_prob = 0.2

# 周期加成
if cycle == "preheat": +0.15
if cycle == "peak": +0.25
if cycle == "release": +0.10

# 離線時長加成
hours_offline = (now - last_message_at) / 3600
if hours_offline > 8: +0.1
if hours_offline > 12: +0.15

最終概率 = min(0.6, base_prob + cycle_bonus + offline_bonus)
```

#### 2.2 夢境主題提取

```python
def extract_dream_seed(state) -> DreamSeed
```

**主題來源：**
1. 從 `state.memory_bank` 隨機選取 1-2 條記憶
2. 結合當前情緒（stress, fatigue）和身體狀態（tension, heat）
3. 生成自然語言主題

**強度判定：**
```python
if tension > 70 or heat > 70:
    intensity = "high"
elif tension > 40 or heat > 40:
    intensity = "medium"
else:
    intensity = "low"
```

**標籤分類：**
```python
if tension > 60 and heat > 60:
    tags.append("intimate")
if stress > 0.6:
    tags.append("anxious")
if body_sum < 200:  # 身體平靜
    tags.append("sweet")
if tension < 30:
    tags.append("released")
```

#### 2.3 夢境餘波效果

```python
def apply_dream_after_effect(state, dream_tags: List[str]) -> dict
```

夢境會在醒來後 **8 小時內** 對身體狀態產生影響：

| 夢境標籤 | 身體效果 |
|---------|---------|
| `intimate` | tension +12, heat +10, sensitivity +6 |
| `anxious` | tension +8, sensitivity +10 |
| `sweet` | tension +5, heat +8, control +5 |
| `released` | tension -18, heat -12, control +8 |

### 使用示例

```python
from app.intimacy.dream import maybe_create_dream_trigger, extract_dream_seed, apply_dream_after_effect

now = datetime.now()
last_message_at = getattr(state, 'last_user_message_at', None)

# 檢查是否應該觸發夢境
if maybe_create_dream_trigger(state, now, last_message_at):
    # 提取夢境種子
    seed = extract_dream_seed(state)
    
    # 儲存到 state
    state.last_dream_at = now
    state.last_dream_seed = seed
    
    # 施加餘波效果
    deltas = apply_dream_after_effect(state, seed.tags)
    
    print(f"夢境觸發: {seed.theme}")
    print(f"身體變化: {deltas}")
```

### Prompt 集成

只在夢境發生後 8 小時內顯示：

```
【夢境回響】
你剛從一個夢中醒來：夢到與 Anna 親密相處
這個夢會影響你接下來的語氣和情緒。
```

---

## 3. Scheduler 集成

### 自動 Tick 任務

在 `app/main.py` 中新增定時任務，每 10 分鐘自動執行：

```python
def intimacy_tick_job():
    """定時 tick 任務"""
    from datetime import datetime
    from app.intimacy.tick import tick_and_update
    from app.intimacy.dream import maybe_create_dream_trigger
    
    now = datetime.now()
    
    # 1. 推進身體狀態
    tick_and_update(state, now)
    
    # 2. 檢查夢境觸發
    last_message_at = getattr(state, 'last_anchor_at', None)
    if maybe_create_dream_trigger(state, now, last_message_at):
        state.add_log("dream", f"夢境觸發：{state.last_dream_seed}")

scheduler.add_job(
    intimacy_tick_job,
    "interval",
    minutes=10,
)
```

---

## 4. State 擴展

### 新增字段

```python
class AppState:
    # V4 新增：夢境
    last_dream_at: Optional[datetime] = None
    last_dream_seed: Optional[DreamSeed] = None
```

---

## 5. API 使用指南

### 完整 Prompt 生成

```python
from app.intimacy import build_intimacy_prompt
from datetime import datetime

prompt = build_intimacy_prompt(state, datetime.now())
```

**生成的 Prompt 包含以下區塊（按順序）：**
1. 【身體狀態】（V1）
2. 【門檻觸發】（V2）
3. 【身心一致性】（V1）
4. 【關係狀態】（V3）
5. 【當前事件】（V2）
6. 【事件餘波】（V2）
7. 【周期】（V1）
8. **【互動意願】（V4 新增）**
9. **【夢境回響】（V4 新增）**

### 測試工具

執行完整測試：

```bash
cd "/Users/anna2/Desktop/lin111/lin-fastapi-modular V4"
PYTHONPATH=. python3 tests/test_v4.py
```

測試內容：
- ✅ Consent 計算（高/低意願場景）
- ✅ Dream Seed 提取（不同情緒/身體狀態）
- ✅ Dream 觸發判斷（離線時間/概率）
- ✅ 完整 Prompt 生成
- ✅ 夢境餘波效果

---

## 6. 設計亮點

### 6.1 Consent 的三維整合

Consent 不是單純的身體狀態，而是「身體 + 情緒 + 關係」的綜合結果：

- **身體狀態**：提供生理基礎（tension 高 → 想釋放）
- **情緒狀態**：提供心理動機（attachment 高 → 想靠近）
- **關係狀態**：提供安全閾值（safety 高 → 敢表達）

這種三維整合使得 Consent 更加貼近真實的親密關係動態。

### 6.2 夢境的記憶連結

夢境不是憑空生成，而是從「記憶庫」中提取：

```python
# 從最近的記憶中隨機選取 1-2 條
recent_memories = state.memory_bank[-10:]
selected = random.sample(recent_memories, min(2, len(recent_memories)))
```

這確保了夢境主題與最近的互動有連續性，而不是隨機的無意義內容。

### 6.3 離線時段的「留白」處理

夢境系統利用離線時段創造「留白」：

- 離線 3-8 小時：低概率觸發，輕度影響
- 離線 8-12 小時：中概率觸發，中度影響
- 離線 >12 小時：高概率觸發，可能產生強烈餘波

這種設計避免了「永遠在線」的機械感，讓角色有「自己的夜晚」。

### 6.4 餘波的時效性

夢境餘波只持續 8 小時，確保不會長期干擾正常狀態：

```python
if hasattr(state, 'last_dream_at') and state.last_dream_at:
    dream_elapsed = (now - state.last_dream_at).total_seconds() / 3600.0
    if dream_elapsed < 8:  # 只在 8 小時內顯示
        # 顯示夢境回響
```

---

## 7. 未來擴展方向

### 7.1 夢境記憶回溯

可以保存最近 N 個夢境，讓 Lin 在對話中偶爾提及：

```python
state.dream_history = []  # List[DreamSeed]
```

### 7.2 Consent 動態調整

根據 Anna 的行為動態調整 Consent：

- Anna 溫柔 → Consent +5
- Anna 冷淡 → Consent -10

### 7.3 夢境類型擴展

新增更多夢境標籤：

- `playful`：俏皮、輕鬆的夢
- `nostalgic`：懷念過去的夢
- `uncertain`：猶豫、不確定的夢

---

## 8. 版本總結

| 版本 | 核心功能 | 狀態 |
|-----|---------|------|
| V1 | 周期 + 身體 + Tick | ✅ 完成 |
| V2 | 事件 + 門檻 + 餘波 | ✅ 完成 |
| V3 | 關係 Engine | ✅ 完成 |
| **V4** | **Consent + Dream** | ✅ **完成** |

**V4 完整測試結果：**
```
🎉 所有 V4 測試通過！

測試通過率：100%
- Consent 計算：✅
- Dream Seed 提取：✅
- Dream 觸發判斷：✅
- 完整 Prompt 生成：✅
- 夢境餘波效果：✅
```

---

## 9. 快速開始

### 啟動服務

```bash
cd "/Users/anna2/Desktop/lin111/lin-fastapi-modular V4"
python3 -m uvicorn app.main:app --reload
```

服務會自動啟動三個 Scheduler：
1. 主動消息檢查（每 N 分鐘）
2. 記憶回顧（每 7 天）
3. **Intimacy Tick（每 10 分鐘）** ← V4 新增

### 測試 Consent

```python
from app.intimacy import calculate_consent

consent = calculate_consent(
    mood={'attachment': 0.9, 'stress': 0.2, 'fatigue': 0.2},
    body_values={'tension': 85, 'heat': 75, 'sensitivity': 70, 'control': 30},
    relationship={'safety': 75, 'rapport': 70, 'temperature': 65}
)
# → 100.0 (高意願)
```

### 測試 Dream

```python
from app.intimacy.dream import extract_dream_seed

seed = extract_dream_seed(state)
print(f"夢境主題: {seed.theme}")
print(f"強度: {seed.intensity}")
print(f"標籤: {seed.tags}")
```

---

## 10. 貢獻者

- **設計與實現**：Anna & Kiro
- **版本**：V4
- **完成時間**：2026-07-27

---

**祝使用愉快！ 🌙✨**
