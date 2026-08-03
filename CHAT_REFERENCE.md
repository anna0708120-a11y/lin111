好的，这是完整的 Reference 文档内容：

```markdown
# 8 月 1 日版本（589c509）聊天链路 Reference

> **本 Reference 的作用是保护聊天链路，不用于证明 Bug 的 Root Cause。**
> 
> 如果未来发现 Bug，应先比较当前代码与本 Reference 的差异，再决定是否修改，而不是重新设计聊天流程。
>
> **核心原则：除非已经定位到 Root Cause，否则不要修改聊天核心链路。**

---

## **版本信息**
- **Commit**: 589c509
- **状态**: ✅ 本地验证聊天正常（Baseline）
- **验证日期**: 2026-08-01
- **用途**: 作为聊天链路的参考标准

---

## **完整聊天调用链**

### **1. 前端发起聊天**
```
用户输入消息
↓
frontend.py: send()
↓
POST /watch
```

### **2. 后端接收并处理**
```
routes.py: observe_anna(activity)
↓
context = f"Anna说：{activity.activity}"
↓
state.add_conversation_turn("anna", context, session_id=target_session_id)
```

### **3. 生成 Lin 的回复（串流）**
```
routes.py: observe_anna()
↓
for event_type, event_data in brain.generate_reply_stream(context, session_id=target_session_id):
    yield SSE 事件到前端
```

### **4. Brain 处理逻辑**
```python
brain.py: generate_reply_stream(context, session_id=None)
↓
# 初始化
target_session = session_id or state.current_session_id
collector = TraceCollector()

↓
# 检查频率限制
if not state.check_rate_limit():
    return

↓
# 构建 system prompt
system_prompt = build_system_prompt(context, state.recent_memory_text())

↓
# 调用 DeepSeek API（串流）
for event_type, event_data in call_deepseek_stream(system_prompt, ...):
    
    # 处理 content 事件
    if event_type == "content":
        full_content += event_data
        yield ("content", event_data)
    
    # 处理 reasoning 事件
    elif event_type == "reasoning":
        full_reasoning += event_data
        yield ("reasoning", event_data)
    
    # 处理 done 事件（关键！）
    elif event_type == "done":
        # 保存 Lin 的回复到数据库
        if full_content and full_content not in ("信号不好。", "今天额度用完了..."):
            thinking_display = strip_hidden_blocks(full_reasoning) if full_reasoning else None
            state.add_conversation_turn("lin", full_content, thinking=thinking_display, session_id=target_session, trace=collector.export())
        
        yield ("done", {})
```

### **5. 保存到数据库**
```python
state.py: add_conversation_turn(role="lin", content=full_content, ...)
↓
turn = {
    "role": "lin",
    "content": full_content,
    "thinking": thinking_display,
    "time": datetime.now().isoformat(),
    "trace": trace,
}
self.conversation_history.append(turn)

↓
db.insert_conversation_turn(role, content, thinking=thinking, session_id=target_session, trace=trace)
```

```python
db.py: insert_conversation_turn(role, content, ...)
↓
if not _client:
    return

try:
    _client.table("conversation_history").insert({
        "role": role,          # "lin"
        "content": content,    # Lin 的回复内容
        "thinking": thinking,
        "session_id": session_id,
        "trace": trace,
    }).execute()
except Exception as e:
    print(f"[db] 写入对话历史失败: {e}")
```

### **6. 前端显示**
```
frontend.py: processChunk({done, value})
↓
if (done):
    syncChat()  # 从服务器同步最新消息
```

---

## **关键代码片段**

### **brain.py - generate_reply_stream() (约 Line 300)**
```python
def generate_reply_stream(context, app_name=None, use_cache=True, session_id=None):
    collector = TraceCollector()
    target_session = session_id or state.current_session_id
    
    rate_limit_ok = state.check_rate_limit()
    if not rate_limit_ok:
        err_msg = "今天额度用完了，或者刚刚问太快了，等一下再说。"
        return
    
    # ... 构建 system_prompt ...
    
    full_content = ""
    full_reasoning = ""
    
    for event_type, event_data in call_deepseek_stream(system_prompt, max_tokens=config.DEEPSEEK_MAX_TOKENS):
        if event_type == "content":
            full_content += event_data
            yield ("content", event_data)
        
        elif event_type == "reasoning":
            full_reasoning += event_data
            yield ("reasoning", event_data)
        
        elif event_type == "done":
            # ⭐ 关键：保存 Lin 的回复
            if full_content and full_content not in ("信号不好。", "今天额度用完了，或者刚刚问太快了，等一下再说。"):
                thinking_display = strip_hidden_blocks(full_reasoning) if full_reasoning else None
                state.add_conversation_turn("lin", full_content, thinking=thinking_display, session_id=target_session, trace=collector.export())
            
            yield ("done", {})
```

### **state.py - add_conversation_turn() (约 Line 460)**
```python
def add_conversation_turn(self, role, content, thinking=None, image_data=None, session_id=None, trace=None):
    target_session = session_id or self.current_session_id
    
    turn = {
        "role": role,
        "content": content,
        "thinking": thinking,
        "image_data": image_data,
        "time": datetime.now().isoformat(),
        "trace": trace,
    }
    self.conversation_history.append(turn)
    
    db.insert_conversation_turn(role, content, thinking=thinking, image_data=image_data, session_id=target_session, trace=trace)
    
    from app import session as session_module
    session_module.update_session_activity(target_session)
```

### **db.py - insert_conversation_turn() (约 Line 289)**
```python
def insert_conversation_turn(role, content, thinking=None, image_data=None, session_id=None, trace=None):
    if not _client:
        return
    try:
        _client.table("conversation_history").insert({
            "role": role,
            "content": content,
            "thinking": thinking,
            "image_data": image_data,
            "session_id": session_id,
            "trace": trace,
        }).execute()
    except Exception as e:
        print(f"[db] 写入对话历史失败: {e}")
```

---

## **核心链路说明**

以下文件和函数属于**聊天核心链路**。修改前必须确认影响范围：

| 文件 | 函数 | 作用 |
|------|------|------|
| `routes.py` | `observe_anna()` | 接收前端消息，触发串流 |
| `brain.py` | `generate_reply_stream()` | 调用 DeepSeek API，处理串流事件 |
| `deepseek_client.py` | `call_deepseek_stream()` | 解析 API 返回，yield 事件 |
| `state.py` | `add_conversation_turn()` | 保存对话到内存和数据库 |
| `db.py` | `insert_conversation_turn()` | 写入数据库 |
| `frontend.py` | `processChunk()`, `syncChat()` | 前端显示和同步 |

**修改核心链路后必须重新验证：**
- ✅ 发送消息后，Lin 能正常回复
- ✅ 数据库 `conversation_history` 表中有 `role=lin` 的记录
- ✅ 前端能正确显示 Lin 的回复
- ✅ 刷新页面后，聊天记录能正确加载
- ✅ 连续发送 2~3 条消息，确认没有重复、丢失或覆盖

---

## **使用建议**

### **当发现聊天相关 Bug 时：**
1. 对比当前代码与本 Reference 的差异
2. 确认差异是否影响聊天链路
3. 如果确认 Bug 来自后续修改，可优先参考 Reference 恢复相关链路
4. 如果 Reference 本身有 Bug，修改前需明确证据和影响范围

### **当新增功能时：**
- ✅ 新增独立模块不影响核心链路
- ✅ 新增 API 端点不影响 `/watch`
- ✅ 新增前端组件不影响 `processChunk()` 和 `syncChat()`
- ⚠️ 如需修改核心链路，必须保证上述 5 项验证通过

---

**此 Reference 记录了 589c509 版本本地验证正常时的聊天链路，作为未来对比和保护的基准。**
```

请将这个内容复制到仓库的 `CHAT_REFERENCE.md` 文件中。
