-- memory_bank 补充字段：Agent Memory 管理能力第一阶段（created_by + archived）
-- 用途：让 Lin 能区分「自己建立」跟「Anna手动建立」的记忆，
--       并支持逻辑删除（归档），不再用物理 DELETE。
-- 执行方式：在 Supabase SQL Editor 里手动执行一次即可。

-- created_by：标记这条记忆是谁建立的。
-- 默认值 'user' 是有意为之——历史资料（包括Lin过去自动写入但没有这个字段的旧记忆）
-- 一律视为 user 建立，Lin 不能动它们，只有这次修改之后新产生的 agent 记忆才会被正确标记。
ALTER TABLE memory_bank
  ADD COLUMN IF NOT EXISTS created_by TEXT NOT NULL DEFAULT 'user';

-- archived：逻辑删除标记。到期清理、Lin主动封存都只改这个字段，不再物理删除。
ALTER TABLE memory_bank
  ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL DEFAULT FALSE;

-- 可选：加索引方便后续查询未归档记忆（数据量不大时非必需，量大了再加）
-- CREATE INDEX IF NOT EXISTS idx_memory_bank_archived ON memory_bank(archived);
