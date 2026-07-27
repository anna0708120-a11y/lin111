# 多聊天室支持 - 数据库迁移指南

## 概述
参考 Claude 界面，添加多聊天室（Session）管理功能，让用户可以：
- 创建多个独立的聊天室
- 在不同聊天室之间切换
- 每个聊天室有独立的对话历史
- 自动生成聊天室标题（基于首条消息）

## 迁移步骤

### 1. 在 Supabase Dashboard 执行 SQL

打开 Supabase Dashboard → SQL Editor，执行 `migrations/add_session_support.sql` 文件中的 SQL 语句。

这个迁移会：
- 创建 `chat_sessions` 表存储聊天室信息
- 给 `conversation_history` 表添加 `session_id` 字段
- 创建必要的索引
- 把现有对话迁移到一个默认 session

### 2. 验证迁移

执行完成后，在 SQL Editor 运行：

```sql
-- 检查 chat_sessions 表
SELECT * FROM chat_sessions;

-- 检查 conversation_history 的 session_id
SELECT session_id, COUNT(*) as count 
FROM conversation_history 
GROUP BY session_id;
```

应该看到：
- `chat_sessions` 表有一条 "历史对话" 记录
- 所有现有对话都有 `session_id`

### 3. 重启应用

迁移完成后重启应用，新代码会自动：
- 从 `chat_sessions` 表读取聊天室列表
- 加载当前 session 的对话历史
- 在对话时自动更新 session 活跃时间

## 新增 API 接口

```
GET    /sessions              # 获取聊天室列表
POST   /sessions              # 创建新聊天室
POST   /sessions/switch       # 切换聊天室
DELETE /sessions/{session_id} # 删除聊天室
```

## 前端集成建议

参考 Claude 的设计：
1. 左侧边栏显示聊天室列表
2. 点击聊天室切换对话
3. 新对话按钮创建新聊天室
4. 第一条消息自动生成标题（前30字符）
5. 可以长按/右键删除非当前聊天室

## 回滚

如果需要回滚，执行：

```sql
-- 删除索引
DROP INDEX IF EXISTS idx_conversation_session;
DROP INDEX IF EXISTS idx_sessions_updated;

-- 删除 session_id 列
ALTER TABLE conversation_history DROP COLUMN IF EXISTS session_id;

-- 删除 chat_sessions 表
DROP TABLE IF EXISTS chat_sessions;
```

## 注意事项

1. **不能删除当前正在使用的聊天室**：API 会检查并拒绝
2. **session_id 在写入时自动关联**：`add_conversation_turn()` 会自动使用 `state.current_session_id`
3. **自动更新活跃时间**：每次对话都会更新 `chat_sessions.updated_at`
4. **首条消息生成标题**：第一条消息会自动截取前30字符作为标题
