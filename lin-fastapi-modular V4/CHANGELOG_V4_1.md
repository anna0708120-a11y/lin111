# V4.1 更新總結

## 新增功能：Consent Dynamics（互動意願動態調整）

### 核心改進
Lin 的互動意願不再是靜態計算，而是會根據 Anna 的行為動態調整。

### 主要特性

1. **自動行為檢測**
   - 溫柔回應：謝謝、愛你、辛苦了 → +8 (持續12h)
   - 主動關心：還好嗎、需要幫忙 → +6 (持續18h)
   - 親密互動：想你、抱抱、靠近 → +12 (持續24h)
   - 冷淡回應：嗯、哦 → -10 (持續24h)

2. **線性衰減機制**
   - 所有調整隨時間線性衰減
   - 避免單次行為造成永久影響

3. **上限保護**
   - 正向調整上限 +20
   - 負向調整下限 -20
   - 保持情感波動自然性

### 新增文件

```
app/intimacy/consent_dynamics.py    # 核心邏輯
tests/test_v4_1_consent.py          # 單元測試（7個測試全通過）
tests/test_v4_1_api.py              # API 測試
docs/V4_1_CONSENT_DYNAMICS.md       # 完整文檔
```

### 修改文件

```
app/state.py                        # 初始化 consent_dynamics
app/web/routes.py                   # /watch 端點整合行為檢測
                                    # 新增 /intimacy/consent API
app/intimacy/consent.py             # 整合動態調整
app/intimacy/prompt.py              # 顯示最近的調整原因
```

### API 端點

**GET /intimacy/consent**
```json
{
  "base_consent": 65.3,
  "total_adjustment": 14.0,
  "final_consent": 79.3,
  "level": "高",
  "description": "今天比平時更想跟妳親近一點。",
  "adjustments": [
    {"reason": "溫柔回應", "effect": 8.0, "hours_ago": 2.5},
    {"reason": "主動關心", "effect": 6.0, "hours_ago": 5.2}
  ]
}
```

### 測試結果

```
✅ 測試 1: 調整衰減機制
✅ 測試 2: 基本動態調整
✅ 測試 3: 行為檢測
✅ 測試 4: Consent 整合
✅ 測試 5: State 整合
✅ 測試 6: 序列化與反序列化
✅ 測試 7: Prompt 整合

🎉 所有 V4.1 Consent Dynamics 測試通過！
```

### 向後兼容

✅ 完全兼容 V4，無需修改現有功能

### 下一步

1. 啟動服務器測試 API：`uvicorn app.main:app --reload`
2. 運行 API 測試：`python3 tests/test_v4_1_api.py`
3. 觀察實際對話中的 Consent 動態變化

---

**版本**: V4.1  
**日期**: 2026-01-27  
**狀態**: ✅ 開發完成，測試通過
