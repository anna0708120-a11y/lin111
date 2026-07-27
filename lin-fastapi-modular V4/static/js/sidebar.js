/**
 * Sidebar
 * 负责：Toggle, Render list, Delete
 */

class Sidebar {
  constructor(sessionManager) {
    this.sessionManager = sessionManager;
    this.sidebarEl = null;
    this.overlayEl = null;
    this.listEl = null;

    // 回调，由外部注入
    this.onNewChat = null;
    this.onSwitchSession = null;
  }

  init() {
    this.sidebarEl = document.getElementById('sidebar');
    this.overlayEl = document.getElementById('sidebarOverlay');
    this.listEl = document.getElementById('sessionList');

    const menuBtn = document.getElementById('sidebarMenuBtn');
    const closeBtn = document.getElementById('sidebarClose');
    const newBtn = document.getElementById('sidebarNewBtn');

    if (menuBtn) menuBtn.addEventListener('click', () => this.toggle());
    if (closeBtn) closeBtn.addEventListener('click', () => this.close());
    if (this.overlayEl) this.overlayEl.addEventListener('click', () => this.close());
    if (newBtn) newBtn.addEventListener('click', () => this.handleNewChat());
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
  }

  async render() {
    await this.sessionManager.loadSessions();
    const sessions = this.sessionManager.sessions;

    if (sessions.length === 0) {
      this.listEl.innerHTML = '<div class="es">暂无聊天记录</div>';
      return;
    }

    this.listEl.innerHTML = '';
    sessions.forEach(session => {
      const isActive = session.id === this.sessionManager.currentSessionId;
      const item = document.createElement('div');
      item.className = 'sidebar-session' + (isActive ? ' active' : '');

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

      const delBtn = document.createElement('button');
      delBtn.className = 'sidebar-session-delete';
      delBtn.textContent = '✕';
      delBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.handleDelete(session.id);
      });

      item.appendChild(info);
      item.appendChild(delBtn);

      item.addEventListener('click', () => this.handleSwitch(session.id));

      this.listEl.appendChild(item);
    });
  }

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
    if (!confirm('确定要删除这个对话吗？')) return;
    await this.sessionManager.delete(sessionId);
    await this.render();
  }
}
