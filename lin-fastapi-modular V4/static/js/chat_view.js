/**
 * Chat View
 * 负责：渲染消息区、更新标题、滚动、切换动效反馈
 */

// Phase 3: Tool UI 用的轻量转义（项目里原本没有 escapeHtml，避免工具名/结果里混入 HTML 破版）
function _escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str == null ? '' : String(str);
  return div.innerHTML;
}

class ChatView {
  constructor() {
    this.cmEl = null;
    this.headerEl = null;
  }

  init() {
    this.cmEl = document.getElementById('cm');
    this.headerEl = document.getElementById('chatHeader');
  }

  clear() {
    if (!this.cmEl) return;
    this.cmEl.innerHTML = '<div class="clabel">with Lin</div>';
  }

  // Phase 2: 接管完整渲染逻辑（时间分隔线、已读状态、思考过程、头像）
  // Developer Trace: lin 訊息若帶 m.trace，會在氣泡下方預留穩定掛載點（data-message-id），
  // render 完成後只遍歷「帶 trace 的訊息」逐一掛載，不做全域 document 掃描。
  renderMessages(history) {
    console.log('[ChatView] renderMessages called, history.length:', history ? history.length : 0);
    if (!this.cmEl) return;
    
    if (!history || history.length === 0) {
      this.cmEl.innerHTML = '<div class="clabel">with Lin</div><div class="msg lin"><div class="msg-row">' + 
        avatarHtml('lin') + '<div class="bub">打開了？</div></div><div class="mtime2">' + ts() + '</div></div>';
      this.scrollToBottom();
      return;
    }
    
    let html = '<div class="clabel">with Lin</div>';
    history.forEach((m, i) => {
      const cur = m.iso ? new Date(m.iso) : new Date();
      const prev = i > 0 ? history[i - 1] : null;
      const prevTime = prev && prev.iso ? new Date(prev.iso) : null;
      if (!prevTime || (cur - prevTime) > 30 * 60 * 1000) {
        html += '<div class="tdiv">' + fmtDivider(cur) + '</div>';
      }
      const next = i < history.length - 1 ? history[i + 1] : null;
      const nextTime = next && next.iso ? new Date(next.iso) : null;
      const showMeta = !next || next.r !== m.r || (nextTime && (nextTime - cur) > 5 * 60 * 1000);
      let meta = '';
      if (showMeta) {
        const read = m.r === 'anna' && history.slice(i + 1).some(x => x.r === 'lin');
        meta = '<div class="mtime2">' + m.time + (read ? ' · 已讀' : '') + '</div>';
      }
      let thinkHtml = '';
      if (m.r === 'lin' && m.think && window.LinChatPolicy?.showThinking === true) {
        thinkHtml = '<div class="think-toggle" onclick="toggleThink(this)">💭 查看思考過程</div><div class="think-box" style="display:none">' + m.think + '</div>';
      }
      // Phase 3: Tool UI（假数据渲染，未接真实工具）。消息对象带 tool 字段时，渲染工具卡片而非气泡。
      if (m.tool) {
        html += this._renderToolCard(m.tool);
        return; // forEach 内用 return 相当于 continue
      }
      html += '<div class="msg ' + m.r + (showMeta ? '' : ' grouped') + '">' + thinkHtml + '<div class="msg-row">' + avatarHtml(m.r) + '<div class="bub">' + m.t + '</div></div>' + meta + '</div>';
    });
    this.cmEl.innerHTML = html;

    this.scrollToBottom();
  }

  // Phase 3: Tool UI —— 生成单个工具调用卡片的 HTML
  // tool: {
  //   name: string,            // 工具标识，例如 'github_search_repo'
  //   status: string,          // 开放枚举，未知状态一律 fallback 到中性样式，不报错
  //   title?: string,          // 可选，优先于 name 显示在卡头
  //   message?: string,        // 单行/多行简短消息（取代旧的 result 字段）
  //   details?: string[]       // 逐行详情列表，例如 Codex 读取文件清单、GitHub commit hash 列表
  // }
  // 设计目的：status 为开放枚举，新增 Codex/GitHub/MCP 等工具的新状态时不需要改这个函数，
  // 只要在 CSS 里加对应的 .tool-card.<status> 规则即可；未定义的状态会 fallback 到中性图标 + 原样文字。
  _renderToolCard(tool) {
    const iconMap = {
      running: '⏳', waiting: '⏳', streaming: '⏳',
      success: '✅', error: '⚠️', cancelled: '✖️',
      paused: '⏸️', custom: '🔧',
    };
    const labelMap = {
      running: '執行中', waiting: '等待中', streaming: '進行中',
      success: '完成', error: '錯誤', cancelled: '已取消',
      paused: '已暫停', custom: '自訂',
    };
    const status = tool.status || 'running';
    // 未知状态（没有对应 CSS 规则的 status）统一 fallback 到 .tool-card.custom，
    // 避免样式空白；已知状态才用自己的 class，让 CSS 里的专属配色生效。
    const knownStatuses = ['running', 'waiting', 'streaming', 'success', 'error', 'cancelled', 'paused', 'custom'];
    const icon = iconMap[status] || '🔧';
    const label = labelMap[status] || _escapeHtml(status);
    const cardClass = knownStatuses.includes(status) ? status : 'custom';
    const name = _escapeHtml(tool.title || tool.name || 'unknown_tool');
    const messageHtml = tool.message ? '<div class="tool-card-message">' + _escapeHtml(tool.message) + '</div>' : '';
    let detailsHtml = '';
    if (Array.isArray(tool.details) && tool.details.length > 0) {
      detailsHtml = '<ul class="tool-card-details">' +
        tool.details.map(d => '<li>' + _escapeHtml(d) + '</li>').join('') +
        '</ul>';
    }
    return '<div class="tool-card ' + cardClass + '">' +
      '<div class="tool-card-head"><span class="tool-card-icon">' + icon + '</span>' +
      '<span class="tool-card-name">' + name + '</span>' +
      '<span class="tool-card-status">' + label + '</span></div>' +
      messageHtml + detailsHtml + '</div>';
  }

  // Phase 3: 测试用 —— 用假数据渲染工具调用卡片，覆盖开放枚举状态 + title/message/details 结构
  // 用法（浏览器 console）：window.chatView.renderToolUIDemo()
  renderToolUIDemo() {
    if (!this.cmEl) return;
    const demoTools = [
      { name: 'github_search_repo', status: 'running', message: 'Searching commits...' },
      {
        name: 'codex_read_repo', status: 'success', title: 'Reading repository',
        message: 'Finished', details: ['app/state.py', 'app/web/frontend.py', 'static/js/chat_view.js'],
      },
      { name: 'codex_run_command', status: 'error', message: '權限不足：無法執行 shell 指令' },
      {
        name: 'mcp_supabase', status: 'streaming', title: 'Calling Supabase',
        message: 'Connected', details: ['Querying...'],
      },
      { name: 'unknown_future_tool', status: 'weird_new_status', message: '未知狀態 fallback 測試' },
    ];
    let html = '<div class="clabel">Tool UI Demo（假數據，開放枚舉）</div>';
    demoTools.forEach(t => { html += this._renderToolCard(t); });
    this.cmEl.innerHTML = html;
    this.scrollToBottom();
  }

  // 追加单条新消息到内存缓存并重画（实时发送/接收时用）
  appendLiveMessage(role, text, think, trace) {
    if (typeof chatMemoryCache === 'undefined') return;
    const entry = { r: role, t: text, time: ts(), iso: new Date().toISOString() };
    if (think) entry.think = think;
    if (trace) entry.trace = trace;
    if (role === 'lin') { entry.message_id = 'live-' + Date.now(); }
    chatMemoryCache.push(entry);
    if (chatMemoryCache.length > 200) chatMemoryCache = chatMemoryCache.slice(-200);
    this.renderMessages(chatMemoryCache);
  }

  // 用数据库回来的整段历史一次性渲染，不写 localStorage。
  // Session 切换 / 新建时的 replay 走这条路径。
  renderHistory(messages) {
    if (typeof renderOnly === 'function') {
      renderOnly(messages || []);
    }
  }

  // 换头像等场景：用当前内存缓存重画
  refresh() {
    if (typeof chatMemoryCache !== 'undefined') {
      this.renderMessages(chatMemoryCache);
    }
  }

  addMessage(role, text, think, animate = true) {
    // 旧接口兼容层，Phase 3 可移除
    this.appendLiveMessage(role, text, think);
  }

  updateHeader(title) {
    if (!this.headerEl) return;
    this.headerEl.style.opacity = '0';
    setTimeout(() => {
      this.headerEl.textContent = title || '新对话';
      this.headerEl.style.opacity = '1';
    }, 150);
  }

  scrollToBottom() {
    if (!this.cmEl) return;
    this.cmEl.scrollTop = this.cmEl.scrollHeight;
  }

  showFeedback(text) {
    if (!this.cmEl) return;
    const tip = document.createElement('div');
    tip.className = 'es';
    tip.style.padding = '6px';
    tip.style.fontSize = '11px';
    tip.textContent = text;
    this.cmEl.appendChild(tip);
    setTimeout(() => tip.remove(), 1200);
  }
}
