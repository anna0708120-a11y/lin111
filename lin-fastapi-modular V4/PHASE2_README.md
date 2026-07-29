# Phase 2: Memory Trace - 完整可觀測性

## 📋 概述

Phase 2 為 Memory 系統添加**完整的執行鏈路追蹤**，記錄每次記憶決策從模型輸出到資料庫寫入的全過程。

### 目標
- **可觀測性**：記錄 Decision → Parser → Backend → DB 的完整流程
- **除錯能力**：快速定位 parse 失敗、衝突、skip 的原因
- **數據驅動**：統計成功率、失敗分布，優化 prompt 和邏輯

---

## 🗂️ 新增檔案

### 1. **Schema**
```
schema_phase2_trace.sql
```
- 新增 `memory_traces` 表，記錄每次決策的完整鏈路
- 索引優化查詢性能

### 2. **核心模組**
```
app/memory_trace.py
```
- `MemoryTrace` dataclass：記錄鏈路的資料結構
- `start_trace()` / `record_*()` / `save_trace()`：收集鏈路
- 全局 `_current_trace` 追蹤當前決策

### 3. **DB 函數**
```
app/db.py (新增)
```
- `insert_memory_trace(trace)`：寫入 trace
- `load_memory_traces(limit, session_id, action_taken)`：查詢 traces
- `get_memory_trace_stats(days)`：統計數據（成功率、失敗分布）

### 4. **整合到 brain.py**
```
app/agent/brain.py (修改)
```
- 在 `think_and_reply()` 中：
  - `start_trace()` 開始追蹤
  - `record_model_output()` 記錄模型輸出
  - `record_parse_result()` 記錄 parse 結果
  - `record_backend_action()` 記錄 backend 執行
  - `record_db_result()` 記錄 DB 操作
  - `save_trace()` 儲存到資料庫

### 5. **修改 state.py**
```
app/state.py (修改)
```
- `remember_or_reinforce()` / `update_memory()` / `archive_memory()` 回傳完整 `dict`：
  ```python
  {
      "memory_id": int,
      "action_taken": "created" | "reinforced" | "updated" | "archived" | "pending_review" | "skipped",
      "conflict_with": int | None,
      "skip_reason": str | None
  }
  ```

---

## 📊 Memory Trace 資料結構

### `memory_traces` 表欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| **會話資訊** | | |
| `session_id` | TEXT | 會話 ID |
| `message_id` | TEXT | 訊息 ID |
| `created_at` | TIMESTAMP | 建立時間 |
| **Step 1: 模型輸出** | | |
| `reasoning_text` | TEXT | 完整的 reasoning（含 [MEMORY_DECISION]） |
| `raw_decision_block` | TEXT | 提取的 [MEMORY_DECISION]...[/MEMORY_DECISION] |
| **Step 2: Parser** | | |
| `parse_success` | BOOLEAN | parse 是否成功 |
| `parsed_decision` | JSONB | parse 成功後的 decision object |
| `parse_error` | TEXT | parse 失敗的錯誤訊息 |
| **Step 3: Backend** | | |
| `backend_action` | TEXT | 執行的函數名 |
| `action_taken` | TEXT | created / reinforced / updated / archived / pending_review / skipped |
| `skip_reason` | TEXT | 跳過原因（如果有） |
| `conflict_with` | BIGINT | 衝突的舊記憶 id |
| **Step 4: DB** | | |
| `memory_id` | BIGINT | 最終寫入/更新的 memory id |
| `db_success` | BOOLEAN | DB 操作是否成功 |
| `db_error` | TEXT | DB 錯誤訊息 |

### Skip Reason 枚舉

| 原因 | 說明 |
|------|------|
| `worth_no` | 模型判斷不值得記 |
| `parse_failed` | 解析 [MEMORY_DECISION] 失敗 |
| `already_exists` | keyword 已存在且內容相似（reinforce） |
| `conflict_detected` | 衝突待審核 |
| `permission_denied` | 試圖修改 user 建立的記憶 |
| `db_error` | 資料庫操作失敗 |

---

## 🔍 使用方式

### 1. 部署 Schema
```bash
# 在 Supabase SQL Editor 中執行
schema_phase2_trace.sql
```

### 2. 查詢 Traces
```python
from app import db

# 最近 50 條 traces
traces = db.load_memory_traces(limit=50)

# 特定 session 的 traces
traces = db.load_memory_traces(session_id="abc123")

# 只看 skipped 的
traces = db.load_memory_traces(action_taken="skipped")

# 統計數據（最近 7 天）
stats = db.get_memory_trace_stats(days=7)
print(stats)
# {
#     "total_count": 100,
#     "success_count": 85,
#     "parse_fail_count": 5,
#     "success_rate": 85.0,
#     "skip_distribution": {
#         "parse_failed": 5,
#         "already_exists": 8,
#         "conflict_detected": 2
#     },
#     "days": 7
# }
```

### 3. Debug 流程
當遇到記憶未正確儲存時：
1. 查詢 `memory_traces` 找到對應的 trace
2. 檢查 `parse_success`：
   - `false` → 查看 `parse_error` 和 `raw_decision_block`
   - `true` → 繼續
3. 檢查 `action_taken`：
   - `skipped` → 查看 `skip_reason`
   - `pending_review` → 查看 `conflict_with`
   - 其他 → 檢查 `db_success` 和 `db_error`

---

## 📈 監控指標

### 成功率監控
```sql
-- 最近 7 天的成功率
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN parse_success AND db_success AND action_taken != 'skipped' THEN 1 ELSE 0 END) as success,
    ROUND(
        SUM(CASE WHEN parse_success AND db_success AND action_taken != 'skipped' THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 
        2
    ) as success_rate
FROM memory_traces
WHERE created_at > NOW() - INTERVAL '7 days';
```

### Parse 失敗分析
```sql
-- Parse 失敗的原因
SELECT 
    parse_error,
    COUNT(*) as count
FROM memory_traces
WHERE parse_success = false
GROUP BY parse_error
ORDER BY count DESC;
```

### Skip 原因分布
```sql
-- Skip 原因統計
SELECT 
    skip_reason,
    COUNT(*) as count
FROM memory_traces
WHERE skip_reason IS NOT NULL
GROUP BY skip_reason
ORDER BY count DESC;
```

### 衝突分析
```sql
-- 產生衝突的記憶
SELECT 
    conflict_with,
    COUNT(*) as conflict_count
FROM memory_traces
WHERE conflict_with IS NOT NULL
GROUP BY conflict_with
ORDER BY conflict_count DESC;
```

---

## 🎯 Phase 2 完成指標

- ✅ Schema 部署完成
- ✅ `memory_trace.py` 模組完成
- ✅ DB 函數完成
- ✅ `brain.py` 整合完成
- ✅ `state.py` 回傳 dict 完成
- ⏳ 測試驗證（執行幾次對話，確認 traces 正確寫入）
- ⏳ 監控儀表板（可選）

---

## 🔄 與 Phase 1 的關係

Phase 1 解決「記憶衝突」問題：
- Keyword normalization
- Conflict detection
- `pending_review` 機制

Phase 2 解決「可觀測性」問題：
- 記錄 Phase 1 的決策過程
- 追蹤衝突如何產生
- 統計 parse 失敗率

兩者互補：Phase 1 是「做什麼」，Phase 2 是「記錄做了什麼」。

---

## 🚀 下一步

### Phase 3 候選方向：
1. **Memory Review UI**：Web 介面審核 `pending_review` 記憶
2. **Auto-conflict Resolution**：自動解決低風險衝突
3. **Memory Merge**：合併相似記憶
4. **Trace Analytics Dashboard**：可視化 trace 數據

---

## 📝 測試步驟

1. 部署 Schema：
   ```bash
   # 在 Supabase 執行 schema_phase2_trace.sql
   ```

2. 啟動服務並對話：
   ```bash
   python -m app.main
   # 發送幾條訊息，觸發記憶決策
   ```

3. 驗證 traces：
   ```python
   from app import db
   traces = db.load_memory_traces(limit=10)
   print(traces)
   ```

4. 檢查統計：
   ```python
   stats = db.get_memory_trace_stats(days=1)
   print(stats)
   ```

---

## 🎉 Phase 2 完成

所有檔案已建立，commit 並 push 到 `feat/phase2-memory-trace` 分支。
