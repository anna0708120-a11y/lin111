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

  addMessage(role, text, think, animate = true) {
    if (!this.cmEl) return;
    // 与既有 addMsg/smsg 保持一致的结构,复用页面已有渲染函数
    if (typeof smsg === 'function') {
      smsg(role, text, think);
    }
  }

  // 用数据库回来的整段历史一次性渲染，不写 localStorage。
  // Session 切换 / 新建时的 replay 走这条路径，避免污染共享的聊天缓存。
  renderHistory(messages) {
    if (typeof renderOnly === 'function') {
      renderOnly(messages || []);
    }
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
