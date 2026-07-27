/**
 * Session Manager
 * 负责：Sessions CRUD, Switch API
 */

class SessionManager {
  constructor(apiBase) {
    this.apiBase = apiBase;
    this.sessions = [];
    this.currentSessionId = null;
  }

  async init() {
    await this.loadSessions();
    if (this.sessions.length === 0) return;

    // 恢復上次的 session（UI 狀態存在 localStorage.lin_current_session）
    // 如果找不到（session 已刪除），退回最近一條
    const saved = localStorage.getItem('lin_current_session');
    const exists = saved && this.sessions.find(s => s.id === saved);
    this.currentSessionId = exists ? saved : this.sessions[0].id;

    // 立即通知後端同步 current_session_id，確保前後端一致
    await this._notifySwitch(this.currentSessionId);
  }

  async loadSessions() {
    try {
      const res = await fetch(this.apiBase + '/chat-sessions');
      const data = await res.json();
      this.sessions = data.sessions || [];
      return this.sessions;
    } catch (err) {
      console.error('Failed to load sessions:', err);
      this.sessions = [];
      return [];
    }
  }

  getCurrentSession() {
    return this.sessions.find(s => s.id === this.currentSessionId) || null;
  }

  async getMessages(sessionId) {
    try {
      const res = await fetch(this.apiBase + '/chat-sessions/' + sessionId);
      const data = await res.json();
      return data.messages || [];
    } catch (err) {
      console.error('Failed to load messages:', err);
      return [];
    }
  }

  async createNew(title = '新对话') {
    try {
      const res = await fetch(this.apiBase + '/chat-sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title })
      });
      const data = await res.json();
      if (data.session_id) {
        this.currentSessionId = data.session_id;
        localStorage.setItem('lin_current_session', data.session_id); // 持久化 UI 狀態
        await this._notifySwitch(data.session_id);
        await this.loadSessions();
        return data.session_id;
      }
      return null;
    } catch (err) {
      console.error('Failed to create session:', err);
      return null;
    }
  }

  async switchTo(sessionId) {
    try {
      this.currentSessionId = sessionId;
      localStorage.setItem('lin_current_session', sessionId); // 持久化 UI 狀態
      await this._notifySwitch(sessionId);
      return true;
    } catch (err) {
      console.error('Failed to switch session:', err);
      return false;
    }
  }

  async delete(sessionId) {
    try {
      await fetch(this.apiBase + '/chat-sessions/' + sessionId, { method: 'DELETE' });
      if (this.currentSessionId === sessionId) {
        this.currentSessionId = null;
      }
      await this.loadSessions();
      return true;
    } catch (err) {
      console.error('Failed to delete session:', err);
      return false;
    }
  }

  async _notifySwitch(sessionId) {
    await fetch(this.apiBase + '/sessions/switch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    });
  }
}
