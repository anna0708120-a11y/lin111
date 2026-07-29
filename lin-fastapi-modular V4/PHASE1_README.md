# Phase 1: Agent Memory Management - 實作文檔

## 概述

Phase 1 實作了基礎的記憶衝突偵測與人工審核機制，解決 Lin 自己建立的記憶可能互相矛盾的問題。

### 核心功能

1. **Keyword Normalization** - 輕量級關鍵字正規化
   - 統一大小寫、去空白
   - 繁簡轉換（朱古力 → chocolate）
   - 同義詞映射（開心/高興 → happy）

2. **Conflict Detection** - 衝突偵測
   - 基於正規化後的 keyword 查找既有記憶
   - 內容相似度 > 70% → 強化（reinforce）
   - 內容相似度 < 70% → 衝突（conflict）→ 標記 pending_review

3. **Pending Review Mechanism** - 待審核機制
   - 衝突記憶標記 `pending_review = TRUE`
   - 記錄 `conflict_with` (舊記憶 id)
   - 不加入 prompt（避免影響對話）
   - 等 Anna 審核後才生效

4. **REST API** - 前端管理接口
   - `GET /api/memory/pending` - 列出待審核記憶
   - `POST /api/memory/approve/:id` - 批准（可選歸檔舊記憶）
   - `POST /api/memory/reject/:id` - 拒絕（直接歸檔）
   - `GET /api/memory/conflicts/summary` - 衝突統計

---

## 檔案結構

```
lin-fastapi-modular V4/
├── schema_phase1.sql                    # 資料庫 Schema 變更
├── app/
│   ├── keyword_normalizer.py           # 關鍵字正規化
│   ├── memory_conflict.py              # 衝突偵測邏輯
│   ├── db_phase1_patch.py              # 資料庫函數補丁
│   ├── state_phase1_patch.py           # State 層補丁
│   ├── agent/
│   │   └── brain_phase1_patch.py       # Brain 整合補丁
│   └── api/
│       └── memory_review.py            # REST API
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
- `raw_keyword` (TEXT) - 模型原始輸出的 keyword

### 2. 啟用 Phase 1 功能

有兩種方式：

#### 方式 A：在 `app/main.py` 中註冊 API（推薦）

```python
from app.api.memory_review import router as memory_review_router

app = FastAPI()
app.include_router(memory_review_router)
```

#### 方式 B：在 `brain.py` 中手動調用（可選）

```python
# 在 brain.py 的 generate_reply() 中
if decision:
    from app.agent.brain_phase1_patch import handle_memory_decision_v2
    result = handle_memory_decision_v2(decision)
    
    if result.get("pending_review"):
        # 可選：通知 Anna 有新的待審核記憶
        pass
```

#### 方式 C：全局遷移到 v2（最激進）

```python
# 在 app 啟動時執行一次
from app.agent.brain_phase1_patch import migrate_to_v2
migrate_to_v2()

# 之後所有 state.remember_or_reinforce() 自動走 v2 邏輯
```

### 3. 測試

```bash
# 單元測試（不需要資料庫）
python test_phase1_memory.py

# 手動測試衝突偵測
# 1. 插入一條記憶：keyword='chocolate', content='Anna 喜歡吃朱古力'
# 2. 插入衝突記憶：keyword='巧克力', content='Anna 不喜歡吃朱古力'
# 3. 查看資料庫：SELECT * FROM memory_bank WHERE pending_review = TRUE;
```

---

## 使用流程

### 對話中自動觸發

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
   → 不加入 prompt（避免混亂）
   ```

### Anna 審核

1. **查看待審核記憶**
   ```bash
   curl http://localhost:8000/api/memory/pending
   ```
   
   回傳：
   ```json
   {
     "pending_memories": [
       {
         "id": 123,
         "content": "Anna 現在不太喜歡吃朱古力了",
         "keyword": "chocolate",
         "conflict_with": 120,
         "conflicting_memory": {
           "id": 120,
           "content": "Anna 喜歡吃朱古力"
         }
       }
     ]
   }
   ```

2. **批准新記憶（歸檔舊的）**
   ```bash
   curl -X POST http://localhost:8000/api/memory/approve/123
   ```
   
   效果：
   - 新記憶 (id=123) 的 `pending_review` 設為 FALSE
   - 舊記憶 (id=120) 被歸檔 (`archived = TRUE`)

3. **拒絕新記憶（保留舊的）**
   ```bash
   curl -X POST http://localhost:8000/api/memory/reject/123
   ```
   
   效果：
   - 新記憶 (id=123) 直接歸檔
   - 舊記憶 (id=120) 保持不變

---

## 設計決策

### 為什麼用 Keyword + Content Similarity？

**Phase 1 目標：輕量級、快速部署**
- Keyword normalization：簡單有效，覆蓋 80% 常見情況
- Content similarity：字符重疊率（Jaccard），不需要 embedding
- Phase 2 再升級為 embedding cosine similarity

### 為什麼不自動解決衝突？

**人類決策的優勢：**
- 語境理解：「我喜歡朱古力」vs「我現在不喜歡」→ 偏好改變，非矛盾
- 時間敏感性：「今天想吃」vs「平常不吃」→ 兩者都對
- 信任建立：Anna 保留最終決策權，增加對系統的信任

### 為什麼 Pending Review 不加入 Prompt？

**避免混亂：**
- Prompt 應該只包含「確定有效」的記憶
- 待審核記憶可能是錯的，不該影響對話
- 審核通過後再加入，保持 prompt 質量

---

## 未來擴展 (Phase 2+)

### Phase 2: Embedding-based Similarity
- 用 sentence-transformers 計算 embedding
- Cosine similarity 取代 Jaccard
- 更準確的語義衝突偵測

### Phase 3: Temporal Reasoning
- 識別「時間相關」的記憶（今天 vs 平常）
- 自動標記「過期」的偏好變化
- 建立 timeline 視圖

### Phase 4: Confidence Scoring
- 每條記憶附帶置信度分數
- 低置信度自動觸發審核
- 高置信度減少打擾

### Phase 5: Batch Review UI
- 前端拖拽式衝突解決界面
- 一次審核多條相關記憶
- 支持「合併」操作（保留兩者精華）

---

## 常見問題

### Q1: 如何添加新的同義詞？

**方式 1：修改 `app/keyword_normalizer.py`**
```python
SYNONYM_MAP = {
    # ...
    "新詞": "target_word",
}
```

**方式 2：運行時動態添加**
```python
from app.keyword_normalizer import add_synonym
add_synonym("新詞", "target_word")
```

### Q2: 衝突判斷太敏感/太寬鬆怎麼辦？

調整 `app/memory_conflict.py` 中的閾值：
```python
# 原本：similarity > 0.7 視為強化
if _content_similarity(new_content, old_content) > 0.7:

# 改為更嚴格（更容易觸發衝突）
if _content_similarity(new_content, old_content) > 0.85:

# 改為更寬鬆（更少衝突）
if _content_similarity(new_content, old_content) > 0.6:
```

### Q3: 如何回滾到 v1（無衝突檢查）？

```python
from app.agent.brain_phase1_patch import rollback_to_v1
rollback_to_v1()
```

### Q4: 待審核記憶太多怎麼辦？

**短期方案：**
- 調高相似度閾值（減少誤判）
- 批量批准/拒絕（開發 batch API）

**長期方案：**
- Phase 4: 自動過濾低置信度衝突
- Phase 5: UI 改進（拖拽式批量處理）

---

## 監控與維護

### 關鍵指標

1. **Pending Review 積壓量**
   ```sql
   SELECT COUNT(*) FROM memory_bank WHERE pending_review = TRUE;
   ```

2. **每日衝突數量**
   ```sql
   SELECT DATE(created_at), COUNT(*) 
   FROM memory_bank 
   WHERE pending_review = TRUE 
   GROUP BY DATE(created_at);
   ```

3. **Top 衝突 Keywords**
   ```sql
   SELECT keyword, COUNT(*) as conflict_count
   FROM memory_bank 
   WHERE pending_review = TRUE 
   GROUP BY keyword 
   ORDER BY conflict_count DESC 
   LIMIT 10;
   ```

### 維護建議

- **每週審核一次** - 避免積壓
- **監控相似度閾值效果** - 根據審核結果調整
- **擴展同義詞表** - 根據實際出現的詞彙補充

---

## 總結

Phase 1 提供了：
✅ 基礎的衝突偵測（keyword + content similarity）  
✅ 人工審核機制（pending review）  
✅ REST API（前端管理）  
✅ 向後相容（v1/v2 並存）  

適合場景：
- 快速部署，立即解決「記憶矛盾」問題
- 不需要複雜的 ML 模型
- Anna 願意參與審核（建立信任）

下一步：
- 部署到生產環境
- 收集數據（衝突類型、審核決策）
- 準備 Phase 2（Embedding-based）
