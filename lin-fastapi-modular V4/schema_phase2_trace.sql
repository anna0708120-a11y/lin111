-- Phase 2: Memory Trace Schema
-- 記錄每次 Memory 決策的完整鏈路，用於可觀測性與除錯

CREATE TABLE IF NOT EXISTS memory_traces (
    id BIGSERIAL PRIMARY KEY,
    
    -- 會話資訊
    session_id TEXT,
    message_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Step 1: 模型輸出
    reasoning_text TEXT,                  -- 完整的 reasoning（含 [MEMORY_DECISION]）
    raw_decision_block TEXT,              -- 提取的 [MEMORY_DECISION]...[/MEMORY_DECISION]
    
    -- Step 2: Parser
    parse_success BOOLEAN DEFAULT FALSE,
    parsed_decision JSONB,                -- parse 成功後的 decision object
    parse_error TEXT,                     -- parse 失敗的錯誤訊息
    
    -- Step 3: Backend
    backend_action TEXT,                  -- remember_or_reinforce / update_memory / archive_memory
    action_taken TEXT,                    -- created / reinforced / pending_review / skipped / updated / archived
    skip_reason TEXT,                     -- 為什麼 skip（如果有）
    conflict_with BIGINT,                 -- 衝突的舊記憶 id（如果有）
    
    -- Step 4: DB
    memory_id BIGINT,                     -- 最終寫入/更新的 memory id
    db_success BOOLEAN DEFAULT TRUE,
    db_error TEXT
);

-- 索引優化查詢
CREATE INDEX IF NOT EXISTS idx_memory_traces_created_at ON memory_traces(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_traces_session_id ON memory_traces(session_id);
CREATE INDEX IF NOT EXISTS idx_memory_traces_action_taken ON memory_traces(action_taken);
CREATE INDEX IF NOT EXISTS idx_memory_traces_memory_id ON memory_traces(memory_id) WHERE memory_id IS NOT NULL;

-- 為了查詢統計數據
CREATE INDEX IF NOT EXISTS idx_memory_traces_parse_success ON memory_traces(parse_success) WHERE parse_success = FALSE;
CREATE INDEX IF NOT EXISTS idx_memory_traces_skip_reason ON memory_traces(skip_reason) WHERE skip_reason IS NOT NULL;

COMMENT ON TABLE memory_traces IS 'Phase 2: 記錄每次 Memory 決策的完整執行鏈路';
COMMENT ON COLUMN memory_traces.reasoning_text IS '模型完整的 reasoning 輸出';
COMMENT ON COLUMN memory_traces.raw_decision_block IS '提取的 [MEMORY_DECISION] block';
COMMENT ON COLUMN memory_traces.parsed_decision IS 'parse 後的 decision object (JSONB)';
COMMENT ON COLUMN memory_traces.action_taken IS 'created/reinforced/pending_review/skipped/updated/archived';
COMMENT ON COLUMN memory_traces.skip_reason IS 'worth_no/parse_failed/already_exists/conflict_detected/permission_denied/db_error';
