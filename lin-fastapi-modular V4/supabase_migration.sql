-- 创建 chat_sessions 表
CREATE TABLE IF NOT EXISTS public.chat_sessions (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  title TEXT NOT NULL DEFAULT '新对话',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 为 conversation_history 添加 session_id 列
ALTER TABLE public.conversation_history 
ADD COLUMN IF NOT EXISTS session_id TEXT REFERENCES public.chat_sessions(id) ON DELETE CASCADE;

-- 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_conversation_history_session_id 
ON public.conversation_history(session_id);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at 
ON public.chat_sessions(updated_at DESC);

-- 刷新 schema 缓存
NOTIFY pgrst, 'reload schema';
