"""
前端页面（监控台 / 对话 / 记忆库）。
这部分是从原本 main.py 里原封不动搬过来的，没有改动任何 UI 或逻辑，
只是单纯挪到自己的文件里，让 main.py 不用再塞几百行 HTML/CSS/JS。
"""

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lin - 正在看著妳</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }
        .profile {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }
        .avatar {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        .info h2 { color: #fff; margin-bottom: 5px; }
        .status { color: #10b981; font-size: 14px; }
        .stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 15px;
        }
        .stat-card {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 12px;
            text-align: center;
        }
        .stat-value { font-size: 24px; font-weight: bold; color: #667eea; }
        .stat-label { font-size: 12px; color: #9ca3af; margin-top: 5px; }
        .content-section {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
            display: none;
        }
        .content-section.active { display: block; }
        .chat-box {
            height: 400px;
            overflow-y: auto;
            margin-bottom: 15px;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
        }
        .message {
            margin-bottom: 15px;
            padding: 12px 16px;
            border-radius: 12px;
            max-width: 80%;
            word-wrap: break-word;
        }
        .user-msg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin-left: auto;
            text-align: right;
        }
        .ai-msg {
            background: rgba(255,255,255,0.1);
            margin-right: auto;
        }
        .ai-msg .thinking {
            color: #fbbf24;
            font-style: italic;
            margin-bottom: 10px;
            padding: 8px;
            background: rgba(251, 191, 36, 0.1);
            border-radius: 8px;
            border-left: 3px solid #fbbf24;
        }
        .ai-msg .content {
            color: #e0e0e0;
        }
        .input-group {
            display: flex;
            gap: 10px;
        }
        .input-group input {
            flex: 1;
            padding: 12px 16px;
            border: none;
            border-radius: 12px;
            background: rgba(255,255,255,0.1);
            color: #fff;
            font-size: 14px;
        }
        .input-group input::placeholder { color: #9ca3af; }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); }
        .nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(26, 26, 46, 0.95);
            backdrop-filter: blur(10px);
            display: flex;
            justify-content: space-around;
            padding: 15px 0;
            box-shadow: 0 -4px 12px rgba(0,0,0,0.2);
        }
        .nav-item {
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            padding: 8px 16px;
            border-radius: 12px;
        }
        .nav-item:hover, .nav-item.active {
            background: rgba(102, 126, 234, 0.2);
            color: #667eea;
        }
        .memory-list { max-height: 400px; overflow-y: auto; }
        .memory-item {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 12px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .memory-item:hover { background: rgba(255,255,255,0.1); transform: translateX(5px); }
        .calendar {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 8px;
            margin-top: 15px;
        }
        .calendar-day {
            aspect-ratio: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .calendar-day:hover { background: rgba(255,255,255,0.1); }
        .calendar-day.period { background: #ef4444; color: #fff; }
        .calendar-day.predicted { background: #fbbf24; color: #fff; }
        .calendar-day.fertile { background: #10b981; color: #fff; }
        /* 模型选择器样式 */
        .model-config-wrapper {
            margin: 20px 0;
        }
        .model-config-header {
            cursor: pointer;
            padding: 15px;
            background: rgba(102, 126, 234, 0.1);
            border-radius: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s;
        }
        .model-config-header:hover {
            background: rgba(102, 126, 234, 0.2);
        }
        .model-config-header span:first-child {
            font-weight: bold;
            font-size: 16px;
        }
        .model-config-body {
            display: none;
            padding: 20px;
            border: 1px solid rgba(102, 126, 234, 0.3);
            border-radius: 12px;
            margin-top: 10px;
            background: rgba(0,0,0,0.2);
        }
        .model-config-body.show {
            display: block;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            font-weight: bold;
            display: block;
            margin-bottom: 8px;
            color: #e0e0e0;
        }
        .form-group select,
        .form-group input {
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 14px;
        }
        .form-group select:focus,
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
            background: rgba(255,255,255,0.08);
        }
        .save-status {
            margin-top: 15px;
            text-align: center;
            font-weight: 600;
            display: none;
        }
        .save-status.show {
            display: block;
        }
        .save-status.success { color: #10b981; }
        .save-status.error { color: #ef4444; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="profile">
                <div class="avatar">🌙</div>
                <div class="info">
                    <h2>Lin</h2>
                    <div class="status">🟢 在線</div>
                </div>
            </div>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value" id="api-count">0</div>
                    <div class="stat-label">今日 API 呼叫</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="memory-count">0</div>
                    <div class="stat-label">記憶總數</div>
                </div>
            </div>
        </div>

        <!-- Home Section -->
        <div id="home-section" class="content-section active">
            <h3 style="margin-bottom: 15px;">📡 實時監控日誌</h3>
            <div class="chat-box" id="monitor-log">
                <p style="color: #9ca3af;">等待監控觸發...</p>
            </div>
        </div>

        <!-- Chat Section -->
        <div id="chat-section" class="content-section">
            <h3 style="margin-bottom: 15px;">💬 與 Lin 對話</h3>
            <div class="chat-box" id="chat-messages"></div>
            <div class="input-group">
                <input type="text" id="user-input" placeholder="輸入訊息..." onkeypress="if(event.key==='Enter') sendMessage()">
                <button class="btn btn-primary" onclick="sendMessage()">↑</button>
            </div>
        </div>

        <!-- Memory Section -->
        <div id="memory-section" class="content-section">
            <h3 style="margin-bottom: 15px;">🧠 長期記憶</h3>
            <div class="memory-list" id="memory-list">
                <p style="color: #9ca3af;">尚無記憶</p>
            </div>
            <div style="margin-top: 15px;">
                <input type="text" id="new-memory" placeholder="新增記憶..." style="width: 100%; padding: 12px; border-radius: 12px; border: none; background: rgba(255,255,255,0.1); color: #fff;">
                <button class="btn btn-primary" style="width: 100%; margin-top: 10px;" onclick="addMemory()">💾 儲存記憶</button>
            </div>
        </div>

        <!-- Mine Section -->
        <div id="mine-section" class="content-section">
            <h3 style="margin-bottom: 15px;">🌙 Mine</h3>
            
            <!-- 经期记录 -->
            <div style="margin-bottom: 30px;">
                <h4 style="margin-bottom: 15px;">📅 經期記錄</h4>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <button class="btn" onclick="prevMonth()" style="background: rgba(255,255,255,0.1); color: #fff;">❮</button>
                    <span id="calendar-month" style="font-weight: bold; font-size: 16px;">2026年7月</span>
                    <button class="btn" onclick="nextMonth()" style="background: rgba(255,255,255,0.1); color: #fff;">❯</button>
                </div>
                <div class="calendar" id="calendar"></div>
                <div style="display: flex; gap: 15px; margin-top: 15px; font-size: 12px;">
                    <span><span style="display: inline-block; width: 12px; height: 12px; background: #ef4444; border-radius: 50%; margin-right: 5px;"></span>已記錄</span>
                    <span><span style="display: inline-block; width: 12px; height: 12px; background: #fbbf24; border-radius: 50%; margin-right: 5px;"></span>預測</span>
                    <span><span style="display: inline-block; width: 12px; height: 12px; background: #10b981; border-radius: 50%; margin-right: 5px;"></span>易孕期</span>
                </div>
            </div>

            <!-- 模型选择器 -->
            <div class="model-config-wrapper">
                <div class="model-config-header" onclick="toggleModelConfig()">
                    <span>🤖 LLM 模型設置</span>
                    <span id="config-arrow">▼</span>
                </div>
                <div id="model-config-body" class="model-config-body">
                    <div class="form-group">
                        <label>選擇模型:</label>
                        <select id="model-selector">
                            <option value="deepseek-chat">DeepSeek Chat</option>
                            <option value="deepseek-reasoner">DeepSeek Reasoner (思維鏈)</option>
                            <option value="claude-3.5-sonnet">Claude 3.5 Sonnet (TODO)</option>
                            <option value="gpt-4o">GPT-4o (TODO)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>API Key:</label>
                        <input type="password" id="api-key" placeholder="輸入 API Key">
                    </div>
                    <button class="btn btn-primary" style="width: 100%;" onclick="saveModelConfig()">💾 保存設置</button>
                    <div id="save-status" class="save-status"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Navigation -->
    <div class="nav">
        <div class="nav-item active" onclick="switchSection('home')">
            <div style="font-size: 24px;">🏠</div>
            <div style="font-size: 12px; margin-top: 5px;">Home</div>
        </div>
        <div class="nav-item" onclick="switchSection('chat')">
            <div style="font-size: 24px;">💬</div>
            <div style="font-size: 12px; margin-top: 5px;">Chat</div>
        </div>
        <div class="nav-item" onclick="switchSection('memory')">
            <div style="font-size: 24px;">🧠</div>
            <div style="font-size: 12px; margin-top: 5px;">Memory</div>
        </div>
        <div class="nav-item" onclick="switchSection('mine')">
            <div style="font-size: 24px;">🌙</div>
            <div style="font-size: 12px; margin-top: 5px;">Mine</div>
        </div>
    </div>

    <script>
        // 页面切换
        function switchSection(section) {
            document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            
            document.getElementById(section + '-section').classList.add('active');
            event.currentTarget.classList.add('active');
        }

        // === 模型选择器功能 ===
        
        // 页面加载时读取保存的配置
        window.addEventListener('DOMContentLoaded', () => {
            const savedModel = localStorage.getItem('llm_model');
            const savedKey = localStorage.getItem('llm_api_key');
            if (savedModel) document.getElementById('model-selector').value = savedModel;
            if (savedKey) document.getElementById('api-key').value = savedKey;
        });

        // 展开/收起模型配置
        function toggleModelConfig() {
            const body = document.getElementById('model-config-body');
            const arrow = document.getElementById('config-arrow');
            
            if (body.classList.contains('show')) {
                body.classList.remove('show');
                arrow.textContent = '▼';
            } else {
                body.classList.add('show');
                arrow.textContent = '▲';
            }
        }

        // 保存模型配置
        function saveModelConfig() {
            const model = document.getElementById('model-selector').value;
            const apiKey = document.getElementById('api-key').value;
            
            if (!apiKey) {
                showSaveStatus('請輸入 API Key', 'error');
                return;
            }
            
            // 保存到 localStorage
            localStorage.setItem('llm_model', model);
            localStorage.setItem('llm_api_key', apiKey);
            
            // 保存到后端
            fetch('/state/update_model', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({model_name: model, api_key: apiKey})
            })
            .then(r => r.json())
            .then(data => {
                showSaveStatus('✓ 保存成功！', 'success');
            })
            .catch(err => {
                showSaveStatus('保存失敗: ' + err, 'error');
            });
        }

        // 显示保存状态
        function showSaveStatus(message, type) {
            const status = document.getElementById('save-status');
            status.textContent = message;
            status.className = 'save-status show ' + type;
            setTimeout(() => {
                status.classList.remove('show');
            }, 3000);
        }

        // === Streaming Chat 功能 ===
        
        function sendMessage() {
            const input = document.getElementById('user-input');
            const msg = input.value.trim();
            if (!msg) return;
            
            const chatBox = document.getElementById('chat-messages');
            
            // 显示用户消息
            const userMsgDiv = document.createElement('div');
            userMsgDiv.className = 'message user-msg';
            userMsgDiv.textContent = msg;
            chatBox.appendChild(userMsgDiv);
            
            // 清空输入框
            input.value = '';
            
            // 创建 AI 消息容器
            const aiMsgDiv = document.createElement('div');
            aiMsgDiv.className = 'message ai-msg';
            aiMsgDiv.innerHTML = '<div class="thinking" style="display:none;"></div><div class="content"></div>';
            chatBox.appendChild(aiMsgDiv);
            
            const thinkingDiv = aiMsgDiv.querySelector('.thinking');
            const contentDiv = aiMsgDiv.querySelector('.content');
            
            // 滚动到底部
            chatBox.scrollTop = chatBox.scrollHeight;
            
            // 调用 streaming API
            const es = new EventSource(`/chat/stream?activity=${encodeURIComponent(msg)}&app_name=聊天界面`);
            
            es.addEventListener('message', (e) => {
                const data = JSON.parse(e.data);
                
                if (data.type === 'thinking') {
                    thinkingDiv.style.display = 'block';
                    thinkingDiv.textContent += data.token;
                } else if (data.type === 'content') {
                    contentDiv.textContent += data.token;
                } else if (data.type === 'done') {
                    es.close();
                }
                
                // 自动滚动
                chatBox.scrollTop = chatBox.scrollHeight;
            });
            
            es.onerror = () => {
                es.close();
                contentDiv.textContent += '\n[連接中斷]';
            };
        }

        // === 其他原有功能 ===
        
        function addMemory() {
            const input = document.getElementById('new-memory');
            const memory = input.value.trim();
            if (!memory) return;
            
            fetch('/memory/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content: memory})
            })
            .then(r => r.json())
            .then(data => {
                input.value = '';
                loadMemories();
            });
        }

        function loadMemories() {
            fetch('/memory/list')
            .then(r => r.json())
            .then(data => {
                const list = document.getElementById('memory-list');
                if (data.memories.length === 0) {
                    list.innerHTML = '<p style="color: #9ca3af;">尚無記憶</p>';
                } else {
                    list.innerHTML = data.memories.map(m => 
                        `<div class="memory-item">${m.content}</div>`
                    ).join('');
                }
                document.getElementById('memory-count').textContent = data.memories.length;
            });
        }

        // 经期日历
        let currentDate = new Date(2026, 6, 1); // 2026年7月

        function renderCalendar() {
            const calendar = document.getElementById('calendar');
            const year = currentDate.getFullYear();
            const month = currentDate.getMonth();
            
            document.getElementById('calendar-month').textContent = `${year}年${month + 1}月`;
            
            const firstDay = new Date(year, month, 1).getDay();
            const daysInMonth = new Date(year, month + 1, 0).getDate();
            
            calendar.innerHTML = '';
            
            // 空白日期
            for (let i = 0; i < firstDay; i++) {
                calendar.innerHTML += '<div class="calendar-day" style="opacity: 0;"></div>';
            }
            
            // 实际日期
            for (let day = 1; day <= daysInMonth; day++) {
                const dayDiv = document.createElement('div');
                dayDiv.className = 'calendar-day';
                dayDiv.textContent = day;
                
                // 示例：标记一些日期
                if (day >= 15 && day <= 20) dayDiv.classList.add('period');
                else if (day >= 21 && day <= 25) dayDiv.classList.add('predicted');
                else if (day >= 10 && day <= 14) dayDiv.classList.add('fertile');
                
                calendar.appendChild(dayDiv);
            }
        }

        function prevMonth() {
            currentDate.setMonth(currentDate.getMonth() - 1);
            renderCalendar();
        }

        function nextMonth() {
            currentDate.setMonth(currentDate.getMonth() + 1);
            renderCalendar();
        }

        // 初始化
        renderCalendar();
        loadMemories();
        
        // 定时刷新 API 计数
        setInterval(() => {
            fetch('/state/stats')
            .then(r => r.json())
            .then(data => {
                document.getElementById('api-count').textContent = data.api_count || 0;
            });
        }, 5000);
    </script>
</body>
</html>
"""
