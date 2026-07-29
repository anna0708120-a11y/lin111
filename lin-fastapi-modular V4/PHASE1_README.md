# Phase 1: Agent Memory Management - 實作文檔

## 概述

Phase 1 實作了基礎的記憶衝突偵測與人工審核機制，解決 Lin 自己建立的記憶可能互相矛盾的問題。

核心邏輯直接整合進既有模組（`db.py` / `state.py`），不另外維護一套 patch 邏輯。
API 層與前端審核界面延後到後續階段再做。

### 核心功能

1. **Keyword Normalization** - 輕量級關鍵字正規化
   - 統一大小寫、去空白
   - 繁簡轉換（朱古力 → chocolate）
   - 同義詞映射（開心/高興 → happy）

2. **Conflict Detection** - 衝突偵測
   - 基於正規化後的 keyword 查找既有記憶（只找 `created_by="agent"` 的）
   - 內容相似度 > 70% → 強化（reinforce）
   - 內容相似度 < 70% → 衝突（conflict）→ 標記 pending_review

3. **Pending Review Mechanism** - 待審核機制
   - 衝突記憶標記 `pending_review = TRUE`
   - 記錄 `conflict_with` (舊記憶 id)
   - 不加入內存 `memory_bank`（避免影響 prompt / 對話）
   - 目前只落地在資料庫，審核 UI/API 延後

---

## 檔案結構

```
lin-fastapi-modular V4/
├── schema_phase1.sql                    # 資料庫 Schema 變更
├── app/
│   ├── keyword_normalizer.py           # 關鍵字正規化
│   ├── memory_conflict.py              # 衝突偵測邏輯（直接依賴 db.py）
│   ├── db.py                           # 已合併 find_conflicting_memories 等 Phase 1 函數
│   └── state.py                        # remember_or_reinforce/update_memory/archive_memory 已整合衝突檢查
├── test_phase1_memory.py               # 測試腳本
└── PHASE1_README.md                    # 本文檔
```

---

## 安裝與部署

### 1. 資料庫 Schema 更新

```bash
# 連接到 Supabase，執行 schema_phase1.sql
psql -h <your-db-host> -U postgres -d postgres -f schema_phase1.sql
```

**新增欄位：**
- `pending_review` (BOOLEAN) - 是否待審核
- `conflict_with` (BIGINT) - 衝突的舊記憶 id
- `raw_keyword` (TEXT) - 模型原始輸出的 keyword（未正規化，供人類查看）

### 2. 直接生效，無需額外接線

`state.py` 的 `remember_or_reinforce` / `update_memory` / `archive_memory` 已經直接呼叫
`app.memory_conflict` 做衝突檢查，`brain.py` 不需要任何修改就能受益。

---

## 測試

```bash
# 單元測試（不需要資料庫）
python test_phase1_memory.py

# 手動測試衝突偵測
# 1. 插入一條記憶：keyword='chocolate', content='Anna 喜歡吃朱古力'
# 2. 插入衝突記憶：keyword='巧克力', content='Anna 不喜歡吃朱古力'
# 3. 查看資料庫：SELECT * FROM memory_bank WHERE pending_review = TRUE;
```

---

## 使用流程（對話中自動觸發）

1. **正常情況（無衝突）**
   ```
   User: 我最近很喜歡吃朱古力
   Lin: (判斷值得記) -> 建立記憶
   → keyword='chocolate', content='Anna 喜歡吃朱古力', pending_review=FALSE
   ```

2. **強化情況（內容相似）**
   ```
   User: 我超愛吃朱古力！
   Lin: (找到舊記憶，內容相似度 > 70%) -> 強化
   → 提高 importance，延長 expires_at
   ```

3. **衝突情況（內容矛盾）**
   ```
   User: 我現在不太喜歡吃朱古力了
   Lin: (找到舊記憶，內容相似度 < 70%) -> 標記衝突
   → 建立新記憶：pending_review=TRUE, conflict_with=<舊記憶id>
   → 不加入內存/prompt（避免混亂），等待人工審核（API/UI 待後續階段）
   ```

---

## Ownership 與 Archive 原則（既有邏輯，本次補明文）

- `created_by="user"` 的記憶，Lin 只能 reinforce，不能 update/archive/conflict-execute。
  `find_memory_by_keyword(..., created_by="agent")` 已確保 update/archive 只命中 Lin 自己建立的記憶。
- Lin 沒有任何函數能物理刪除記憶；`archive_memory` 一律是邏輯刪除（`archived=True`）。

---

## 設計決策

### 為什麼用 Keyword + Content Similarity？

**Phase 1 目標：輕量級、快速部署**
- Keyword normalization：簡單有效，覆蓋常見高頻詞，之後發現重複再補
- Content similarity：字符重疊率（Jaccard），不需要 embedding
- Phase 2 再視需要升級為 embedding cosine similarity

### 為什麼不自動解決衝突？

**人類決策的優勢：**
- 語境理解：「我喜歡朱古力」vs「我現在不喜歡」→ 偏好改變，非矛盾
- 時間敏感性：「今天想吃」vs「平常不吃」→ 兩者都對
- 信任建立：Anna 保留最終決策權，增加對系統的信任

### 為什麼 Pending Review 不加入內存/Prompt？

**避免混亂：**
- Prompt 應該只包含「確定有效」的記憶
- 待審核記憶可能是錯的，不該影響對話
- 審核通過後再加入，保持 prompt 質量

---

## 這一輪不做的（延後）

- `resolve_conflict()` API / 審核 REST 接口
- Memory Inspector（前端監控台審核界面）
- Tool Calling

---

## 未來擴展 (Phase 2+)

- **Phase 2**: Embedding-based similarity（更準確的語義衝突偵測）
- **Phase 3**: Temporal reasoning（識別「今天 vs 平常」等時間相關記憶）
- **Phase 4**: Confidence scoring（自動過濾低置信度衝突）
- **Phase 5**: API + Batch review UI（審核界面正式落地）

---

## 常見問題

### Q1: 如何添加新的同義詞？

```python
from app.keyword_normalizer import add_synonym
add_synonym("新詞", "target_word")
```

或直接編輯 `app/keyword_normalizer.py` 的 `SYNONYM_MAP`。

### Q2: 衝突判斷太敏感/太寬鬆怎麼辦？

調整 `app/memory_conflict.py` 中 `detect_conflict()` 的閾值（目前 0.7）。

### Q3: 待審核記憶怎麼查？

Phase 1 只落地資料庫，暫時用 SQL 查詢：
```sql
SELECT * FROM memory_bank WHERE pending_review = TRUE AND archived = FALSE;
```

審核 API/UI 在後續階段補上。

---

## 監控與維護

### 關鍵指標（SQL 查詢）

```sql
-- Pending Review 積壓量
SELECT COUNT(*) FROM memory_bank WHERE pending_review = TRUE;

-- 每日衝突數量
SELECT DATE(created_at), COUNT(*) 
FROM memory_bank 
WHERE pending_review = TRUE 
GROUP BY DATE(created_at);

-- Top 衝突 Keywords
SELECT keyword, COUNT(*) as conflict_count
FROM memory_bank 
WHERE pending_review = TRUE 
GROUP BY keyword 
ORDER BY conflict_count DESC 
LIMIT 10;
```

---

## 總結

Phase 1 提供了：
✅ 基礎的衝突偵測（keyword + content similarity）
✅ 人工審核標記機制（pending_review，資料庫層面）
✅ 邏輯直接整合進 `db.py` / `state.py`，不維護獨立 patch 模組
⏸ API / UI 延後到後續階段
