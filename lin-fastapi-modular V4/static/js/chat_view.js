/* Chat View: messages plus the single AgentPanel lifecycle surface. */
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
    if (this.cmEl) this.cmEl.innerHTML = '<div class="clabel">with Lin</div>';
  }

  renderMessages(history) {
    if (!this.cmEl) return;
    if (!history || history.length === 0) {
      this.cmEl.innerHTML = '<div class="clabel">with Lin</div><div class="msg lin"><div class="msg-row">' +
        avatarHtml('lin') + '<div class="bub">打開了？</div></div><div class="mtime2">' + ts() + '</div></div>';
      this.scrollToBottom();
      return;
    }

    const agentSlots = [];
    let html = '<div class="clabel">with Lin</div>';
    history.forEach((message, index) => {
      const current = message.iso ? new Date(message.iso) : new Date();
      const previous = index > 0 ? history[index - 1] : null;
      const previousTime = previous && previous.iso ? new Date(previous.iso) : null;
      if (!previousTime || current - previousTime > 30 * 60 * 1000) {
        html += '<div class="tdiv">' + fmtDivider(current) + '</div>';
      }

      const next = index < history.length - 1 ? history[index + 1] : null;
      const nextTime = next && next.iso ? new Date(next.iso) : null;
      const showMeta = !next || next.r !== message.r || (nextTime && nextTime - current > 5 * 60 * 1000);
      const read = message.r === 'anna' && history.slice(index + 1).some((item) => item.r === 'lin');
      const meta = showMeta ? '<div class="mtime2">' + message.time + (read ? ' · 已讀' : '') + '</div>' : '';
      const messageId = message.message_id != null ? String(message.message_id) : null;
      const agentSlot = message.r === 'lin' && messageId ? '<div class="agent-panel-slot" data-message-id="' + messageId + '"></div>' : '';
      if (message.r === 'lin' && messageId && message.trace) agentSlots.push({ messageId, trace: message.trace });
      html += '<div class="msg ' + message.r + (showMeta ? '' : ' grouped') + '">' + agentSlot + '<div class="msg-row">' +
        avatarHtml(message.r) + '<div class="bub">' + message.t + '</div></div>' + meta + '</div>';
    });

    this.cmEl.innerHTML = html;
    agentSlots.forEach(({ messageId, trace }) => {
      const slot = this.cmEl.querySelector('.agent-panel-slot[data-message-id="' + CSS.escape(messageId) + '"]');
      if (slot && window.AgentPanel) window.AgentPanel.mountHistory(slot, trace);
    });
    this.scrollToBottom();
  }

  appendLiveMessage(role, text, think, trace) {
    if (typeof chatMemoryCache === 'undefined') return;
    const entry = { r: role, t: text, time: ts(), iso: new Date().toISOString() };
    if (think) entry.think = think;
    if (trace) entry.trace = trace;
    if (role === 'lin') entry.message_id = 'live-' + Date.now();
    chatMemoryCache.push(entry);
    if (chatMemoryCache.length > 200) chatMemoryCache = chatMemoryCache.slice(-200);
    this.renderMessages(chatMemoryCache);
  }

  renderHistory(messages) {
    if (typeof renderOnly === 'function') renderOnly(messages || []);
  }

  refresh() {
    if (typeof chatMemoryCache !== 'undefined' && chatMemoryCache.length > 0) this.renderMessages(chatMemoryCache);
  }

  addMessage(role, text, think) {
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
    if (this.cmEl) this.cmEl.scrollTop = this.cmEl.scrollHeight;
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
