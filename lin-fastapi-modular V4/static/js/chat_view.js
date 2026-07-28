/**
 * Chat View
 * 负责：渲染消息区、更新标题、滚动、切换动效反馈
 */

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
      if (m.r === 'lin' && m.think) {
        thinkHtml = '<div class="think-toggle" onclick="toggleThink(this)">💭 查看思考過程</div><div class="think-box" style="display:none">' + m.think + '</div>';
      }
      html += '<div class="msg ' + m.r + (showMeta ? '' : ' grouped') + '">' + thinkHtml + '<div class="msg-row">' + avatarHtml(m.r) + '<div class="bub">' + m.t + '</div></div>' + meta + '</div>';
    });
    this.cmEl.innerHTML = html;
    this.scrollToBottom();
  }

  // 追加单条新消息到内存缓存并重画（实时发送/接收时用）
  appendLiveMessage(role, text, think) {
    if (typeof chatMemoryCache === 'undefined') return;
    const entry = { r: role, t: text, time: ts(), iso: new Date().toISOString() };
    if (think) entry.think = think;
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
