-- Migration: 添加多聊天室支持
-- 执行时间：2025-01-XX
-- 说明：参考 Claude 界面，添加 session 管理

-- 1. 创建 chat_sessions 表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '新对话',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_count INTEGER DEFAULT 0
);

-- 2. 给 conversation_history 表添加 session_id 字段
ALTER TABLE conversation_history 
ADD COLUMN IF NOT EXISTS session_id TEXT;

-- 3. 创建索引，加速查询
CREATE INDEX IF NOT EXISTS idx_conversation_session 
ON conversation_history(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sessions_updated 
ON chat_sessions(updated_at DESC);

-- 4. 数据迁移：把现有的对话归到一个默认 session
-- 生成一个默认 session ID
INSERT INTO chat_sessions (id, title, created_at, updated_at, message_count)
VALUES (
    'default-session-' || extract(epoch from now())::text,
    '历史对话',
    NOW(),
    NOW(),
    (SELECT COUNT(*) FROM conversation_history WHERE session_id IS NULL)
)
ON CONFLICT (id) DO NOTHING;

-- 把所有没有 session_id 的对话归到这个默认 session
UPDATE conversation_history
SET session_id = (SELECT id FROM chat_sessions WHERE title = '历史对话' LIMIT 1)
WHERE session_id IS NULL;

-- 5. 设置 session_id 为 NOT NULL（现在所有数据都有了）
-- 注意：Supabase 可能不支持某些 ALTER TABLE 语法，如果报错可以跳过这步
-- ALTER TABLE conversation_history 
-- ALTER COLUMN session_id SET NOT NULL;
