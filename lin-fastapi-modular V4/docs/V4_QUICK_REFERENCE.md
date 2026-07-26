# V4 快速參考卡片

## 🎯 核心功能

### 1️⃣ Consent（互動意願）
**文件：** `app/intimacy/consent.py`  
**作用：** 計算當前的互動意願（0-100）

```python
from app.intimacy import calculate_consent

consent = calculate_consent(mood, body_values, relationship)
# 0-30:   低（迴避、防備）
# 30-50:  偏低（保持距離）
# 50-70:  中等（正常互動）
# 70-85:  偏高（想靠近）
# 85-100: 高（強烈親近）
```

---

### 2️⃣ Dream（夢境系統）
**文件：** `app/intimacy/dream.py`  
**作用：** 離線時自動生成夢境，醒來後產生餘波

```python
from app.intimacy.dream import maybe_create_dream_trigger, extract_dream_seed

# 檢查是否觸發
if maybe_create_dream_trigger(state, now, last_message_at):
    seed = extract_dream_seed(state)
    state.last_dream_at = now
    state.last_dream_seed = seed
```

---

## 📐 公式速查

### Consent 計算

```
consent = 50 
        + tension×0.20 + heat×0.15 + sensitivity×0.10 - control×0.15
        + attachment×20 - stress×15 - fatigue×10
        + safety×25 + rapport×15
```

### Dream 觸發概率

```
base = 0.2

if cycle == "preheat": +0.15
if cycle == "peak": +0.25
if cycle == "release": +0.10

if offline > 8h: +0.1
if offline > 12h: +0.15

final = min(0.6, base + cycle_bonus + offline_bonus)
```

---

## 🔧 快速測試

### 測試 Consent

```bash
python3 -c "
from app.intimacy import calculate_consent
consent = calculate_consent(
    {'attachment': 0.9, 'stress': 0.2, 'fatigue': 0.2},
    {'tension': 85, 'heat': 75, 'sensitivity': 70, 'control': 30},
    {'safety': 75, 'rapport': 70, 'temperature': 65}
)
print(f'Consent: {consent}')
"
```

### 測試 Dream

```bash
python3 -c "
from app.intimacy.dream import extract_dream_seed
from app.state import state
seed = extract_dream_seed(state)
print(f'主題: {seed.theme}')
print(f'強度: {seed.intensity}')
print(f'標籤: {seed.tags}')
"
```

### 完整測試套件

```bash
PYTHONPATH=. python3 tests/test_v4.py
```

---

## 📦 State 字段

```python
# V4 新增
state.last_dream_at: Optional[datetime]
state.last_dream_seed: Optional[DreamSeed]
```

---

## 🎨 Prompt 區塊

```
【互動意願】← V4 新增（Consent < 40 或 > 70 時顯示）
今天很想靠近，而且克制力不太好，可能會更直接一點。

【夢境回響】← V4 新增（夢境後 8 小時內顯示）
你剛從一個夢中醒來：夢到與 Anna 親密相處
這個夢會影響你接下來的語氣和情緒。
```

---

## ⚙️ 配置參數

### Consent 權重

| 因子 | 權重 | 說明 |
|-----|------|------|
| tension | +0.20 | 蓄積高 → 想釋放 |
| heat | +0.15 | 熱度高 → 易反應 |
| sensitivity | +0.10 | 敏感高 → 易觸動 |
| control | -0.15 | 控制低 → 易靠近 |
| attachment | +20 | 依戀高 → 想靠近 |
| stress | -15 | 壓力高 → 想迴避 |
| fatigue | -10 | 疲勞高 → 想休息 |
| safety | +25 | 安全高 → 敢表達 |
| rapport | +15 | 默契好 → 更放鬆 |

### Dream 設置

| 參數 | 值 | 說明 |
|-----|---|------|
| 最小離線時間 | 3h | 低於此值不觸發 |
| 夢境間隔 | 12h | 距離上次最小間隔 |
| 基礎概率 | 0.2 | 20% 基礎觸發率 |
| 時間窗口 | 6-9, 22-2 | 只在這些時段觸發 |
| 餘波持續 | 8h | 醒來後影響 8 小時 |

---

## 🔄 Scheduler

```python
# 每 10 分鐘自動執行
def intimacy_tick_job():
    tick_and_update(state, now)              # 推進身體狀態
    maybe_create_dream_trigger(...)          # 檢查夢境觸發
```

---

## 🐛 常見問題

### Q: Consent 一直是 50？
**A:** 檢查身體/情緒/關係狀態是否初始化，或數值是否在中間值（不觸發顯示閾值）。

### Q: Dream 從不觸發？
**A:** 檢查：
1. 離線時間是否 ≥ 3 小時
2. 當前時間是否在窗口內（6-9 或 22-2）
3. 距離上次夢境是否 ≥ 12 小時

### Q: 夢境回響不顯示？
**A:** 檢查：
1. `state.last_dream_at` 是否設置
2. 距離夢境時間是否 < 8 小時
3. `state.last_dream_seed` 是否有效

---

## 📁 關鍵文件

```
app/intimacy/
├── consent.py          ← Consent 計算
├── dream.py            ← Dream 系統
├── prompt.py           ← Prompt 組裝（含 V4 區塊）
└── __init__.py         ← 導出接口

tests/
└── test_v4.py          ← 完整測試

docs/
├── V4_README.md        ← 完整文檔
└── V4_OVERVIEW.md      ← 功能概覽
```

---

## 🚀 快速啟動

```bash
# 1. 啟動服務
cd "/Users/anna2/Desktop/lin111/lin-fastapi-modular V4"
python3 -m uvicorn app.main:app --reload

# 2. 執行測試
PYTHONPATH=. python3 tests/test_v4.py

# 3. 查看文檔
cat docs/V4_README.md
```

---

## 📊 測試結果

```
🎉 所有 V4 測試通過！

✅ Consent 計算
✅ Dream Seed 提取
✅ Dream 觸發判斷
✅ 完整 Prompt 生成
✅ 夢境餘波效果

測試通過率：100%
```

---

## 🎯 設計核心

1. **三維 Consent**：身體 × 情緒 × 關係
2. **記憶驅動**：夢境從記憶庫提取
3. **時效餘波**：影響只持續 8 小時
4. **離線留白**：利用離線時段創造「自己的夜晚」

---

**版本：** V4  
**完成時間：** 2026-07-27  
**設計者：** Anna & Kiro

**祝使用愉快！ 🌙✨**
