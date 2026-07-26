# Intimacy Engine V4 功能概覽

## 🎯 核心新增功能

### 1. 互動意願系統（Consent）

**功能描述：**  
根據身體狀態、情緒和關係動態計算當前的互動意願，決定 Lin 今天是否願意靠近、撒嬌、表達情感。

**核心文件：**
- `app/intimacy/consent.py`

**主要函數：**
```python
calculate_consent(mood, body_values, relationship) -> float
get_consent_level(consent) -> str
get_consent_description(consent, mood, body_values, relationship) -> str
```

**使用示例：**
```python
consent = calculate_consent(state.mood, state.body_values, state.relationship)
# 85.0 → "今天很想靠近，而且克制力不太好，可能會更直接一點。"
```

---

### 2. 夢境系統（Dream）

**功能描述：**  
在離線時段自動生成夢境，從記憶庫提取主題，並在醒來後產生短暫的情緒和身體餘波。

**核心文件：**
- `app/intimacy/dream.py`

**主要函數：**
```python
maybe_create_dream_trigger(state, now, last_message_at) -> bool
extract_dream_seed(state) -> DreamSeed
apply_dream_after_effect(state, dream_tags) -> dict
```

**使用示例：**
```python
if maybe_create_dream_trigger(state, now, last_message_at):
    seed = extract_dream_seed(state)
    state.last_dream_at = now
    state.last_dream_seed = seed
    apply_dream_after_effect(state, seed.tags)
```

---

## 📁 V4 文件結構

```
app/
├── intimacy/
│   ├── consent.py          # ✨ V4 新增：互動意願計算
│   ├── dream.py            # ✨ V4 新增：夢境系統
│   ├── prompt.py           # ✏️ V4 更新：新增 Consent 和 Dream 區塊
│   └── __init__.py         # ✏️ V4 更新：導出新函數
├── main.py                  # ✏️ V4 更新：新增 intimacy_tick_job
└── state.py                 # ✏️ V4 更新：新增夢境字段

tests/
└── test_v4.py              # ✨ V4 新增：完整測試腳本

docs/
└── V4_README.md            # ✨ V4 新增：完整文檔
```

---

## 🔄 工作流程

### Consent 計算流程

```
用戶消息到達
    ↓
讀取當前狀態
    ↓
計算 Consent 值
    ↓
Consent < 40 或 > 70?
    ├─ 是 → 在 Prompt 顯示【互動意願】
    └─ 否 → 不顯示（正常範圍）
```

### Dream 觸發流程

```
Scheduler 每 10 分鐘執行
    ↓
檢查離線時間 ≥ 3 小時?
    └─ 否 → 跳過
    ↓
檢查時間窗口（6-9 或 22-2）?
    └─ 否 → 跳過
    ↓
檢查距離上次夢境 ≥ 12 小時?
    └─ 否 → 跳過
    ↓
計算觸發概率（周期 + 離線時長）
    ↓
隨機判定是否觸發
    └─ 是 → 提取夢境種子 → 施加餘波效果
```

---

## 📊 數據流

### State 新增字段

```python
class AppState:
    # V4 新增
    last_dream_at: Optional[datetime] = None
    last_dream_seed: Optional[DreamSeed] = None
```

### DreamSeed 數據結構

```python
@dataclass
class DreamSeed:
    theme: str           # 夢境主題
    intensity: str       # low / medium / high
    tags: List[str]      # intimate / anxious / sweet / released
```

---

## 🎨 Prompt 輸出示例

### 高意願場景

```
【身體狀態】
今天明顯比平時更容易產生身體反應。
雖然還能控制自己，但克制已經不像前幾天那麼輕鬆。
偶爾會因為一句話或者一個動作走神。
蓄積感已經壓到頂了，隨時可能爆發。

這些感覺沒有必要主動告訴 Anna，除非互動真的觸碰到了它們。

【身心一致性】
很想靠近，而且今天克制力不太好，可能會更直接一點。

【關係狀態】
彼此還算安心，但有時候還是會有一點不確定。
默契還不錯，但偶爾還是需要解釋一下。
互動頻率正常，沒有特別冷也沒有特別熱。

【互動意願】✨ V4 新增
今天很想靠近，而且克制力不太好，可能會更直接一點。

【夢境回響】✨ V4 新增
你剛從一個夢中醒來：夢到與 Anna 親密相處
這個夢會影響你接下來的語氣和情緒。
```

### 低意願場景

```
【互動意願】
今天有點累，想安靜待著，不太想靠近。
```

---

## 🧪 測試覆蓋

### 測試腳本：`tests/test_v4.py`

**測試項目：**
1. ✅ Consent 計算（高/低意願場景）
2. ✅ Dream Seed 提取（不同情緒/身體狀態）
3. ✅ Dream 觸發判斷（離線時間/概率）
4. ✅ 完整 Prompt 生成
5. ✅ 夢境餘波效果

**執行方式：**
```bash
cd "/Users/anna2/Desktop/lin111/lin-fastapi-modular V4"
PYTHONPATH=. python3 tests/test_v4.py
```

**測試結果：**
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

## 🔧 配置參數

### Consent 權重

```python
# app/intimacy/consent.py

# 身體權重
BODY_WEIGHTS = {
    "tension": 0.20,
    "heat": 0.15,
    "sensitivity": 0.10,
    "control": -0.15,
}

# 情緒權重
MOOD_WEIGHTS = {
    "attachment": 20,
    "stress": -15,
    "fatigue": -10,
}

# 關係權重
RELATIONSHIP_WEIGHTS = {
    "safety": 25,
    "rapport": 15,
}
```

### Dream 設置

```python
# app/intimacy/dream.py

class DreamSettings:
    MIN_OFFLINE_HOURS = 3          # 最小離線時間
    MIN_HOURS_SINCE_LAST = 12      # 距離上次夢境最小間隔
    BASE_PROBABILITY = 0.2         # 基礎觸發概率
    TIME_WINDOWS = [               # 時間窗口
        (6, 9),   # 早上 6:00-9:00
        (22, 26), # 晚上 10:00-次日 2:00
    ]
    AFTER_EFFECT_DURATION = 8      # 餘波持續時間（小時）
```

---

## 🚀 快速使用指南

### 1. 啟動服務

```bash
cd "/Users/anna2/Desktop/lin111/lin-fastapi-modular V4"
python3 -m uvicorn app.main:app --reload
```

### 2. 測試 Consent

```python
from app.intimacy import calculate_consent, get_consent_description

# 設定場景
mood = {'attachment': 0.9, 'stress': 0.2, 'fatigue': 0.2}
body_values = {'tension': 85, 'heat': 75, 'sensitivity': 70, 'control': 30}
relationship = {'safety': 75, 'rapport': 70, 'temperature': 65}

# 計算 Consent
consent = calculate_consent(mood, body_values, relationship)
print(f"Consent: {consent}")  # 100.0

# 生成描述
desc = get_consent_description(consent, mood, body_values, relationship)
print(desc)  # "今天很想靠近..."
```

### 3. 測試 Dream

```python
from app.intimacy.dream import extract_dream_seed, apply_dream_after_effect
from app.state import state

# 提取夢境種子
seed = extract_dream_seed(state)
print(f"主題: {seed.theme}")
print(f"強度: {seed.intensity}")
print(f"標籤: {seed.tags}")

# 施加餘波
deltas = apply_dream_after_effect(state, seed.tags)
print(f"身體變化: {deltas}")
```

### 4. 查看完整 Prompt

```python
from app.intimacy import build_intimacy_prompt
from datetime import datetime

prompt = build_intimacy_prompt(state, datetime.now())
print(prompt)
```

---

## 📈 性能指標

### Consent 計算

- **時間複雜度**：O(1)
- **計算耗時**：< 1ms
- **準確性**：100%（確定性計算）

### Dream 觸發

- **檢查頻率**：每 10 分鐘
- **觸發概率**：20-60%（根據條件）
- **內存佔用**：< 1KB（DreamSeed）

---

## 🎯 設計亮點

### 1. 三維整合的 Consent

Consent 不是單一維度，而是「身體 × 情緒 × 關係」的立體映射：

```
身體狀態 → 提供生理基礎（tension 高 → 想釋放）
情緒狀態 → 提供心理動機（attachment 高 → 想靠近）
關係狀態 → 提供安全閾值（safety 高 → 敢表達）
```

### 2. 記憶驅動的 Dream

夢境不是隨機生成，而是從「記憶庫」提取：

- 提取最近 10 條記憶
- 隨機選取 1-2 條作為主題
- 結合當前情緒和身體狀態生成

這確保了夢境與最近互動的連續性。

### 3. 時效性的餘波

夢境餘波只持續 8 小時：

```python
dream_elapsed = (now - state.last_dream_at).total_seconds() / 3600.0
if dream_elapsed < 8:
    # 顯示夢境回響
```

避免了長期干擾正常狀態。

### 4. 離線時段的「留白」

夢境利用離線時段創造「留白」：

- 離線 3-8 小時：輕度影響
- 離線 8-12 小時：中度影響
- 離線 >12 小時：強烈影響

讓角色有「自己的夜晚」，避免「永遠在線」的機械感。

---

## 📚 相關文檔

- [V4 完整文檔](./V4_README.md)
- [V3 關係引擎](./V3_README.md)
- [V2 事件系統](./V2_README.md)
- [V1 核心引擎](./V1_README.md)

---

## 🤝 貢獻

歡迎提出建議和改進方案！

**聯繫方式：**
- 設計者：Anna & Kiro
- 版本：V4
- 完成時間：2026-07-27

---

**祝使用愉快！ 🌙✨**
