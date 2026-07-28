/**
 * Sidebar
 * 负责：Toggle, Render list, New Chat, Session actions (Rename / Delete / Star with pin-to-top)
 */

class Sidebar {
  constructor(sessionManager) {
    this.sessionManager = sessionManager;
    this.sidebarEl = null;
    this.overlayEl = null;
    this.listEl = null;
    this.newChatBtn = null;

    this._ctxMenuEl = null;
    this._longPressTimer = null;
    this._longPressFired = false;

    // 回调，由外部注入
    this.onNewChat = null;
    this.onSwitchSession = null;
  }

  init() {
    this.sidebarEl = document.getElementById('sidebar');
    this.overlayEl = document.getElementById('sidebarOverlay');
    this.listEl = document.getElementById('sessionList');
    this.newChatBtn = document.getElementById('sidebarNewChatBtn');

    const menuBtn = document.getElementById('sidebarMenuBtn');
    const closeBtn = document.getElementById('sidebarClose');

    if (menuBtn) menuBtn.addEventListener('click', () => this.toggle());
    if (closeBtn) closeBtn.addEventListener('click', () => this.close());
    if (this.overlayEl) this.overlayEl.addEventListener('click', () => this.close());
    if (this.newChatBtn) this.newChatBtn.addEventListener('click', () => this.handleNewChat());

    // 点击空白处关闭 context menu
    document.addEventListener('click', () => this._closeCtxMenu());
    // 侧边栏关闭时一并关闭 context menu
  }

  toggle() {
    const isActive = this.sidebarEl.classList.contains('active');
    if (isActive) {
      this.close();
    } else {
      this.open();
    }
  }

  open() {
    this.sidebarEl.classList.add('active');
    this.overlayEl.classList.add('active');
    this.render();
  }

  close() {
    this.sidebarEl.classList.remove('active');
    this.overlayEl.classList.remove('active');
    this._closeCtxMenu();
  }

  async render() {
    await this.sessionManager.loadSessions();
    // 置顶（starred）排在最前，其余保持后端原有的 updated_at 倒序
    const sessions = [...this.sessionManager.sessions].sort((a, b) => {
      const aStar = a.starred ? 1 : 0;
      const bStar = b.starred ? 1 : 0;
      return bStar - aStar;
    });

    this._closeCtxMenu();
    this.listEl.innerHTML = '';

    this._closeCtxMenu();
    this.listEl.innerHTML = '';

    if (sessions.length === 0) {
      this.listEl.innerHTML = '<div class="es">暂无聊天记录</div>';
      return;
    }

    sessions.forEach(session => {
      this.listEl.appendChild(this._buildSessionRow(session));
    });
  }

  _buildSessionRow(session) {
    const isActive = session.id === this.sessionManager.currentSessionId;
    const item = document.createElement('div');
    item.className = 'sidebar-session' + (isActive ? ' active' : '');
    item.dataset.sessionId = session.id;

    const info = document.createElement('div');
    info.className = 'sidebar-session-info';

    const title = document.createElement('div');
    title.className = 'sidebar-session-title';
    title.textContent = session.title || '新对话';

    const time = document.createElement('div');
    time.className = 'sidebar-session-time';
    time.textContent = session.time || '';

    info.appendChild(title);
    info.appendChild(time);

    // 三点操作按钮（桌面 hover 显示，移动端常驻显示，CSS 已处理）
    const moreBtn = document.createElement('button');
    moreBtn.className = 'sidebar-session-more';
    moreBtn.type = 'button';
    moreBtn.setAttribute('aria-label', '更多操作');
    moreBtn.innerHTML = '<svg viewBox="0 0 16 16" fill="currentColor"><circle cx="3" cy="8" r="1.4"/><circle cx="8" cy="8" r="1.4"/><circle cx="13" cy="8" r="1.4"/></svg>';
    moreBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this._openCtxMenu(session, moreBtn);
    });

    item.appendChild(info);
    item.appendChild(moreBtn);

    // 点击主体切换 session
    info.addEventListener('click', () => this.handleSwitch(session.id));

    // 移动端长按 → 打开操作菜单（不依赖 hover）
    item.addEventListener('touchstart', (e) => {
      this._longPressFired = false;
      this._longPressTimer = setTimeout(() => {
        this._longPressFired = true;
        this._openCtxMenu(session, moreBtn);
      }, 500);
    }, { passive: true });
    item.addEventListener('touchend', () => clearTimeout(this._longPressTimer));
    item.addEventListener('touchmove', () => clearTimeout(this._longPressTimer));
    item.addEventListener('touchcancel', () => clearTimeout(this._longPressTimer));

    return item;
  }

  // ---------- Context Menu (Rename / Star-UI / Delete) ----------

  _closeCtxMenu() {
    if (this._ctxMenuEl) {
      this._ctxMenuEl.remove();
      this._ctxMenuEl = null;
    }
  }

  _openCtxMenu(session, anchorEl) {
    this._closeCtxMenu();

    const menu = document.createElement('div');
    menu.className = 'session-ctx-menu';
    menu.addEventListener('click', (e) => e.stopPropagation());

    const starred = !!session.starred;

    menu.appendChild(this._ctxItem({
      label: starred ? 'Unstar' : 'Star',
      svg: '<path d="M8 1.6l1.9 3.9 4.3.6-3.1 3 .7 4.3L8 11.4 4.2 13.4l.7-4.3-3.1-3 4.3-.6z"/>',
      extraClass: starred ? 'starred' : '',
      onClick: async () => {
        this._closeCtxMenu();
        await this.sessionManager.toggleStar(session.id);
        await this.render();
      }
    }));

    menu.appendChild(this._ctxItem({
      label: 'Rename',
      svg: '<path d="M11 2l3 3-8 8H3v-3z"/>',
      onClick: () => {
        this._closeCtxMenu();
        this._startRename(session);
      }
    }));

    menu.appendChild(document.createElement('div')).className = 'session-ctx-divider';

    const deleteItem = this._ctxItem({
      label: 'Delete',
      svg: '<path d="M3.5 4.5h9M6 4.5V3a1 1 0 011-1h2a1 1 0 011 1v1.5M6.5 7.5v4M9.5 7.5v4M4.5 4.5l.6 8a1 1 0 001 .9h3.8a1 1 0 001-.9l.6-8"/>',
      extraClass: 'danger',
      onClick: () => this._showDeleteConfirm(session, menu)
    });
    menu.appendChild(deleteItem);

    document.body.appendChild(menu);
    this._ctxMenuEl = menu;
    this._positionCtxMenu(menu, anchorEl);
  }

  _ctxItem({ label, svg, extraClass, onClick }) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'session-ctx-item' + (extraClass ? ' ' + extraClass : '');
    btn.innerHTML = `<svg viewBox="0 0 16 16" fill="none">${svg}</svg><span>${label}</span>`;
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      onClick();
    });
    return btn;
  }

  _showDeleteConfirm(session, menu) {
    menu.innerHTML = '';
    menu.addEventListener('click', (e) => e.stopPropagation());

    const confirmText = document.createElement('div');
    confirmText.className = 'session-ctx-confirm';
    confirmText.textContent = `确定要刪除「${session.title || '新对话'}」吗？此操作无法复原。`;
    menu.appendChild(confirmText);

    const actions = document.createElement('div');
    actions.className = 'session-ctx-confirm-actions';

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'session-ctx-confirm-cancel';
    cancelBtn.textContent = '取消';
    cancelBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this._closeCtxMenu();
    });

    const okBtn = document.createElement('button');
    okBtn.type = 'button';
    okBtn.className = 'session-ctx-confirm-ok';
    okBtn.textContent = '刪除';
    okBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      this._closeCtxMenu();
      await this.handleDelete(session.id);
    });

    actions.appendChild(cancelBtn);
    actions.appendChild(okBtn);
    menu.appendChild(actions);
  }

  _positionCtxMenu(menu, anchorEl) {
    const anchorRect = anchorEl.getBoundingClientRect();
    const menuRect = menu.getBoundingClientRect();
    const margin = 8;

    let top = anchorRect.bottom + 4;
    let left = anchorRect.right - menuRect.width;

    if (top + menuRect.height > window.innerHeight - margin) {
      top = anchorRect.top - menuRect.height - 4;
    }
    if (top < margin) top = margin;
    if (left < margin) left = margin;
    if (left + menuRect.width > window.innerWidth - margin) {
      left = window.innerWidth - margin - menuRect.width;
    }

    menu.style.top = `${top}px`;
    menu.style.left = `${left}px`;
  }

  // ---------- Rename ----------

  _startRename(session) {
    const row = this.listEl.querySelector(`.sidebar-session[data-session-id="${CSS.escape(session.id)}"]`);
    if (!row) return;
    const titleEl = row.querySelector('.sidebar-session-title');
    if (!titleEl) return;

    const originalText = session.title || '新对话';
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'sidebar-session-title-input';
    input.value = originalText;
    input.maxLength = 60;

    titleEl.replaceWith(input);
    input.focus();
    input.select();

    let settled = false;
    const commit = async () => {
      if (settled) return;
      settled = true;
      const newTitle = input.value.trim();
      if (newTitle && newTitle !== originalText) {
        await this.sessionManager.rename(session.id, newTitle);
      }
      await this.render();
    };
    const cancel = () => {
      if (settled) return;
      settled = true;
      this.render();
    };

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); commit(); }
      if (e.key === 'Escape') { e.preventDefault(); cancel(); }
    });
    input.addEventListener('blur', () => commit());
    input.addEventListener('click', (e) => e.stopPropagation());
  }

  // ---------- Actions ----------

  async handleNewChat() {
    const sessionId = await this.sessionManager.createNew();
    if (sessionId) {
      this.close();
      if (this.onNewChat) this.onNewChat(sessionId);
    }
  }

  async handleSwitch(sessionId) {
    const ok = await this.sessionManager.switchTo(sessionId);
    if (ok) {
      this.close();
      if (this.onSwitchSession) this.onSwitchSession(sessionId);
    }
  }

  async handleDelete(sessionId) {
    const result = await this.sessionManager.delete(sessionId);
    if (!result || result.ok === false) {
      // 后端拒绝删除（例如：正在删除当前使用中的 session），
      // 前端状态与后端保持一致，不做误导性的乐观更新
      alert((result && result.message) || '删除失败，请稍后再试');
      await this.render();
      return;
    }
    await this.render();
  }
}
