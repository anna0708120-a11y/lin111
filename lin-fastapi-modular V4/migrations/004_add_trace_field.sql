-- 004: conversation_history 新增 trace 欄位，存放 Developer Panel 用的版本化 trace JSON。
-- Nullable，不影響既有資料與既有查詢；舊資料 trace 為 NULL，前端會 fallback 成無 trace 顯示。
ALTER TABLE conversation_history ADD COLUMN IF NOT EXISTS trace JSONB;
