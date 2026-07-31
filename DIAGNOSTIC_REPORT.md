# Lin111 诊断报告 - 2026-07-31

## 问题概述
用户 anna0708120-a11y 报告了三个主要问题：
1. **Event Bus 显示空白**：监控台的 Event Bus 区域一直显示 "📡 等待系統事件..."
2. **Memory 存储和读取异常**：Memory 页面内容无法正确显示
3. **Lin 回复带有隐藏标签**：Lin 的实际回复中出现 `[MOOD_EVENT]...[/MOOD_EVENT]` 标签

---

## 问题 1：Event Bus 显示空白

### 根本原因
**前端逻辑错误**：`llogs()` 函数中的 Event Bus 降级逻辑存在致命缺陷。

**代码位置**：`frontend.py` 第 1906-1926 行

```javascript
// 当前的错误逻辑
if(ev){
  // Event Bus 处理逻辑
  // ...
  lc.innerHTML=html;
} else {
  // 降级：舊 /logs 邏輯
  const sysLogs=[...d.logs].filter(l=>l.type!=='AI回复').reverse().slice(0,15);
  if(sysLogs.length>0){
    lc.innerHTML=sysLogs.map(l=>'<div class="li">...</div>').join('');
  } else {
    lc.innerHTML='<div class="es">📡 等待系統事件...</div>';
  }
}
```

**问题分析**：
1. 当 `/events` 接口返回空数据时，`ev` 变量为 `{}` 或 `null`
2. 代码进入 `if(ev)` 分支（因为空对象 `{}` 是 truthy）
3. `ev.activity` 和 `ev.persistent` 都是 `undefined`
4. 最终 `html` 为空字符串，导致 `lc.innerHTML` 被设置为空
5. 没有触发降级逻辑，也没有显示 "等待系統事件..." 提示

### 修复方案
修改降级判断逻辑，确保只有在 Event Bus 有有效数据时才使用新逻辑：

```javascript
// 修复后的逻辑
if(ev && (ev.activity?.length > 0 || Object.keys(ev.persistent || {}).length > 0)){
  // Event Bus 处理逻辑（只有在有数据时才执行）
  // ...
} else {
  // 降级：舊 /logs 邏輯（Event Bus 空或失败时执行）
  const sysLogs=[...d.logs].filter(l=>l.type!=='AI回复').reverse().slice(0,15);
  if(sysLogs.length>0){
    lc.innerHTML=sysLogs.map(l=>'<div class="li">...</div>').join('');
  } else {
    lc.innerHTML='<div class="es">📡 等待系統事件...</div>';
  }
}
```

---

## 问题 2：Memory 存储和读取异常

### 根本原因
**后端接口实现不完整**：`GET /memory` 接口返回格式与前端期望不匹配。

**代码位置**：`routes.py` 第 335-338 行

```python
@router.get("/memory")
def list_memory():
    """给记忆库分页面用：回传目前所有记忆（来自 Supabase，不是浏览器本地存的）。"""
    return {"memories": state.memory_bank}
```

**问题分析**：
1. `state.memory_bank` 是一个字典结构：`{"长期记忆": [...], "短期记忆": [...], ...}`
2. 前端期望接收分类好的记忆数据，但接口直接返回原始字典
3. 前端可能无法正确解析这种嵌套结构，导致 Memory 页面显示异常

### 修复方案

#### 方案 A：规范化后端返回格式（推荐）
```python
@router.get("/memory")
def list_memory():
    """返回所有记忆，按分类整理。"""
    result = {}
    for category, items in state.memory_bank.items():
        result[category] = [
            {
                "id": m.get("id"),
                "content": m.get("content"),
                "importance": m.get("importance", 0),
                "timestamp": m.get("timestamp", ""),
                "keywords": m.get("keywords", []),
            }
            for m in items
        ]
    return {"memories": result, "total": sum(len(v) for v in result.values())}
```

#### 方案 B：前端兼容处理
如果后端格式无法修改，前端需要添加解析逻辑来处理嵌套字典结构。

---

## 问题 3：Lin 回复带有隐藏标签

### 根本原因
**Content 和 Reasoning 混淆**：`[MOOD_EVENT]` 标签应该只出现在 `reasoning_content` 中，但可能被写入了 `content` 字段。

**代码位置**：
- System Prompt: `persona.py` 第 84 行
- 过滤逻辑: `claude_client.py` 第 145-147 行
- 显示逻辑: `brain.py` 第 409 行

**问题分析**：
1. **System Prompt 指令模糊**：`MOOD_EVENT_INSTRUCTION` 说明 "会显示在监控台头像旁边"，但没有明确说明应该写在 `reasoning` 还是 `content`
2. **Claude 可能误判**：DeepSeek/Claude 可能将 `[MOOD_EVENT]` 标签输出到 `content` 而非 `reasoning_content`
3. **过滤逻辑只针对 reasoning**：`claude_client.py` 中的过滤逻辑只处理 `reasoning_content`，不处理 `content`
4. **前端直接显示 content**：前端的 `contentBuffer` 直接显示从后端接收的 `content`，没有任何过滤

**流程图**：
```
System Prompt (指令模糊)
    ↓
Claude/DeepSeek 输出
    ↓
[MOOD_EVENT] 可能出现在 content ← 核心问题
    ↓
claude_client.py (只过滤 reasoning)
    ↓
brain.py (reasoning 用 strip_hidden_blocks，content 不过滤)
    ↓
前端 contentBuffer (直接显示)
    ↓
用户看到 [MOOD_EVENT] 标签 ❌
```

### 修复方案

#### 方案 A：加强 System Prompt 指令（推荐）
修改 `memory_rules.py` 中的 `MOOD_EVENT_INSTRUCTION`：

```python
MOOD_EVENT_INSTRUCTION = """
## 心情事件判定（写在 <thinking> 标签内，不要出现在正式回复中）

**重要**：以下内容必须写在 <thinking> 标签内（reasoning_content），不要出现在正式回复（content）中。

不用自己打分数、不用算attachment/stress这些数值——数值由程序根据事件自动增减，你只需要判断这一轮最贴近下面哪些事件：

[MOOD_EVENT]
event: 可以选一个，也可以选多个（这一轮同时符合多种情况时），多个事件用逗号分隔
  PRAISE 她夸你/对你好/主动示好
  ...（其他事件定义保持不变）
line: 一句话，此刻的心情，会显示在监控台头像旁边，比如"在等妳的消息"
[/MOOD_EVENT]

**再次提醒**：这段内容只写在思考过程（<thinking>）里，不要出现在给 Anna 的回复中。
"""
```

#### 方案 B：增加 Content 过滤（防御性编程）
即使 System Prompt 明确，也应该在后端增加防御性过滤：

**修改 `brain.py` 第 342-343 行**：
```python
elif event_type == "content":
    # 防御性过滤：确保 content 中不会出现隐藏标签
    cleaned_data = strip_hidden_blocks(data) if data else data
    full_content += cleaned_data
    yield f"event: content\ndata: {json.dumps({'delta': cleaned_data})}\n\n"
```

**或者在前端增加过滤**（`frontend.py` 第 1834 行）：
```javascript
else if(currentEvent === 'content' && data.delta !== undefined){
  // 防御性过滤：移除可能泄漏的隐藏标签
  let cleanDelta = data.delta
    .replace(/\[MOOD_EVENT\][\s\S]*?\[\/MOOD_EVENT\]/g, '')
    .replace(/\[MEMORY_DECISION\][\s\S]*?\[\/MEMORY_DECISION\]/g, '')
    .replace(/\[MOOD_REPORT\][\s\S]*?\[\/MOOD_REPORT\]/g, '');
  
  contentBuffer += cleanDelta;
  // ... 其余逻辑
}
```

#### 方案 C：验证 LLM 输出（最彻底）
在 `claude_client.py` 中增加验证逻辑，检测 `content` 中是否包含隐藏标签：

```python
elif event_type == "content":
    if content_chunk is not None:
        # 检测并警告
        if any(tag in content_chunk for tag in ["[MOOD_EVENT]", "[MEMORY_DECISION]", "[MOOD_REPORT]"]):
            print(f"⚠️  警告：content 中发现隐藏标签，已过滤: {content_chunk[:50]}")
            content_chunk = strip_hidden_blocks(content_chunk)
        yield ("content", content_chunk)
```

---

## 优先级和实施顺序

### 高优先级（立即修复）
1. **问题 3 - 方案 A + 方案 B**：
   - 修改 System Prompt，明确标签位置
   - 在后端 `brain.py` 或前端增加防御性过滤
   - 预计工作量：15-30 分钟

2. **问题 1 - 修复降级逻辑**：
   - 修改 `frontend.py` 的 `llogs()` 函数
   - 预计工作量：10 分钟

### 中优先级（尽快处理）
3. **问题 2 - 规范化后端接口**：
   - 修改 `routes.py` 的 `GET /memory` 接口
   - 测试前端兼容性
   - 预计工作量：30-45 分钟

---

## 测试建议

### 问题 1 测试
1. 清空 Event Bus 数据
2. 刷新监控台页面
3. 验证是否显示 "📡 等待系統事件..." 或降级到旧 logs 显示
4. 发送消息触发事件，验证 Event Bus 是否正常更新

### 问题 2 测试
1. 在 Memory 页面添加新记忆
2. 刷新页面，验证记忆是否正确显示
3. 检查浏览器开发者工具的 Network 标签，查看 `/memory` 接口返回格式
4. 检查浏览器 Console，查看是否有 JavaScript 错误

### 问题 3 测试
1. 发送触发 MOOD_EVENT 的消息（如："谢谢你"）
2. 检查 Lin 的回复是否包含 `[MOOD_EVENT]` 标签
3. 检查监控台的 Event Bus 是否正确显示心情事件
4. 验证 reasoning 部分是否正常过滤（折叠的思考过程应该看不到标签）

---

## 根本原因总结

| 问题 | 根本原因 | 类型 | 严重程度 |
|------|---------|------|---------|
| Event Bus 空白 | 降级逻辑判断错误（空对象是 truthy） | 前端逻辑错误 | 中 |
| Memory 异常 | 接口返回格式与前端期望不匹配 | 接口规范问题 | 中 |
| 隐藏标签泄漏 | System Prompt 指令模糊 + 缺少防御性过滤 | 提示词设计缺陷 | 高 |

所有问题都不是重大架构问题，可以通过局部修改快速修复。

---

## 附录：相关代码位置

- **Event Bus 前端逻辑**：`frontend.py` 第 1894-1938 行
- **Memory 接口**：`routes.py` 第 335-338 行
- **MOOD_EVENT 指令**：`memory_rules.py` 第 96-119 行
- **System Prompt 构建**：`persona.py` 第 50-88 行
- **Content 流处理**：`claude_client.py` 第 105-160 行
- **Brain SSE 输出**：`brain.py` 第 330-420 行
- **前端 Content 显示**：`frontend.py` 第 1820-1860 行

