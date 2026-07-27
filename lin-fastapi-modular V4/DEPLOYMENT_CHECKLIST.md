# 多聊天室功能部署检查清单

## 📋 部署前准备

### 1. 数据库迁移 ✅
- [ ] 在 Supabase Dashboard 执行 `migrations/add_session_support.sql`
- [ ] 验证 `chat_sessions` 表已创建
- [ ] 验证 `conversation_history` 表已添加 `session_id` 字段
- [ ] 检查现有对话是否已迁移到默认 session

### 2. 代码检查 ✅
- [x] `app/session.py` - 新增 session 管理模块
- [x] `app/db.py` - 添加 session 相关数据库操作
- [x] `app/state.py` - 添加当前 session 跟踪和切换逻辑
- [x] `app/web/routes.py` - 添加 session 管理 API

### 3. 本地测试
- [ ] 运行 `python3 test_session.py` 确保功能正常
- [ ] 测试创建新聊天室
- [ ] 测试切换聊天室
- [ ] 测试删除聊天室
- [ ] 测试对话记录是否正确关联到 session

## 🚀 部署步骤

### 1. 备份数据库
```sql
-- 在 Supabase 执行前，先导出现有数据
SELECT * FROM conversation_history;
SELECT * FROM chat_sessions;
```

### 2. 执行数据库迁移
1. 打开 Supabase Dashboard
2. 进入 SQL Editor
3. 复制 `migrations/add_session_support.sql` 内容
4. 执行 SQL
5. 验证执行结果

### 3. 部署代码
```bash
# 提交代码
git add .
git commit -m "feat: 添加多聊天室支持（参考 Claude 界面）"
git push origin main

# Render 会自动部署
```

### 4. 验证部署
```bash
# 检查 API 是否正常
curl https://your-app.onrender.com/sessions

# 应该返回聊天室列表
```

## 🧪 测试清单

### API 测试
- [ ] `GET /sessions` - 获取聊天室列表
- [ ] `POST /sessions` - 创建新聊天室
- [ ] `POST /sessions/switch` - 切换聊天室
- [ ] `DELETE /sessions/{id}` - 删除聊天室

### 功能测试
- [ ] 新建聊天室后，对话记录独立
- [ ] 切换聊天室时，加载对应的对话历史
- [ ] 第一条消息自动生成标题
- [ ] 不能删除当前正在使用的聊天室
- [ ] 删除聊天室后，对话记录也被删除

### 多端同步测试
- [ ] 手机端创建聊天室，电脑端能看到
- [ ] 网页端切换聊天室，手机端自动更新
- [ ] 三端对话记录保持同步

## 🔧 故障排查

### 问题：找不到 session 模块
```bash
# 确保 app/session.py 存在
ls app/session.py
```

### 问题：数据库查询失败
```sql
-- 检查表是否存在
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('chat_sessions', 'conversation_history');
```

### 问题：现有对话丢失
```sql
-- 检查是否有未迁移的对话
SELECT COUNT(*) FROM conversation_history WHERE session_id IS NULL;

-- 如果有，手动迁移
UPDATE conversation_history
SET session_id = (SELECT id FROM chat_sessions LIMIT 1)
WHERE session_id IS NULL;
```

## 📝 回滚计划

如果部署后出现问题，执行：

```sql
-- 1. 移除 session_id 约束
ALTER TABLE conversation_history DROP COLUMN session_id;

-- 2. 删除 chat_sessions 表
DROP TABLE chat_sessions;

-- 3. 回滚代码
git revert HEAD
git push origin main
```

## ✅ 部署完成

- [ ] 数据库迁移完成
- [ ] 代码部署成功
- [ ] API 测试通过
- [ ] 功能测试通过
- [ ] 多端同步正常
- [ ] 更新文档
- [ ] 通知用户新功能

## 🎉 新功能说明

给用户的更新说明：

```
🎉 新功能：多聊天室支持

参考 Claude 界面，现在你可以：
1. 创建多个独立的聊天室
2. 在不同话题之间轻松切换
3. 每个聊天室保持独立的对话历史
4. 自动生成聊天室标题

API 端点：
- GET /sessions - 获取所有聊天室
- POST /sessions - 创建新聊天室
- POST /sessions/switch - 切换聊天室
- DELETE /sessions/{id} - 删除聊天室

建议前端设计：
- 左侧边栏显示聊天室列表
- 点击切换，长按删除
- 新对话按钮醒目
```
