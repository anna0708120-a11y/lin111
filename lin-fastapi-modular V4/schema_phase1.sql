-- Phase 1: Schema Changes for Memory Management
-- 執行此 SQL 前請先備份資料庫

-- 1. Add pending_review column (conflict 待審核標記)
ALTER TABLE memory_bank 
ADD COLUMN IF NOT EXISTS pending_review BOOLEAN DEFAULT FALSE;

-- 2. Add conflict_with column (記錄衝突的舊記憶 id)
ALTER TABLE memory_bank 
ADD COLUMN IF NOT EXISTS conflict_with BIGINT NULL;

-- 3. Add raw_keyword column (保留模型原始輸出的 keyword)
ALTER TABLE memory_bank 
ADD COLUMN IF NOT EXISTS raw_keyword TEXT NULL;

-- 4. Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_memory_bank_keyword ON memory_bank(keyword);
CREATE INDEX IF NOT EXISTS idx_memory_bank_pending_review ON memory_bank(pending_review) WHERE pending_review = TRUE;
CREATE INDEX IF NOT EXISTS idx_memory_bank_conflict_with ON memory_bank(conflict_with) WHERE conflict_with IS NOT NULL;

-- 5. Add foreign key constraint (optional, 確保 conflict_with 指向有效記憶)
-- ALTER TABLE memory_bank 
-- ADD CONSTRAINT fk_memory_bank_conflict_with 
-- FOREIGN KEY (conflict_with) REFERENCES memory_bank(id) ON DELETE SET NULL;
