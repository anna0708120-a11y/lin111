/* Lin single-chat Agent Activity adapter and timeline renderer. */
(function () {
  const MARK = '✦';

  function safeJson(value) {
    if (value == null || value === '') return '';
    if (typeof value === 'string') return value;
    try { return JSON.stringify(value, null, 2); } catch (_) { return String(value); }
  }

  function unwrap(raw) {
    if (!raw || typeof raw !== 'object') return null;
    if (raw.event && typeof raw.event === 'object') return raw.event;
    return raw;
  }

  function typeOf(event) {
    return String(event?.type || event?.event_type || event?.kind || '').toLowerCase();
  }

  function toolId(event) {
    return String(event?.tool_id || event?.tool_call_id || event?.id || '');
  }

  function toolLabel(event) {
    return String(event?.display_name || event?.name || event?.tool_name || 'Tool');
  }

  function detailFor(event) {
    return event?.summary || event?.preview || event?.message || event?.result ||
      event?.error || event?.context || event?.args || event?.input || '';
  }

  function statusText(status) {
    return status === 'complete' ? '完成' : status === 'error' ? '失败' : status === 'progress' ? '进行中' : '执行中';
  }

  class Activity {
    constructor(parent, seed) {
      this.parent = parent;
      this.events = [];
      this.byTool = new Map();
      this.byAgent = new Map();
      this.root = document.createElement('div');
      this.root.className = 'lin-agent-activity';
      this.root.innerHTML = '<div class="lin-agent-live"><span class="lin-agent-mark">✦</span><span class="lin-agent-current">Agent 工作中</span><span class="lin-agent-spinner" aria-hidden="true"></span></div><div class="lin-agent-trail"></div>';
      parent.appendChild(this.root);
      this.live = this.root.querySelector('.lin-agent-live');
      this.current = this.root.querySelector('.lin-agent-current');
      this.trail = this.root.querySelector('.lin-agent-trail');
      if (seed) this.ingest(seed);
    }

    ingest(raw) {
      const event = unwrap(raw);
      const type = typeOf(event);
      if (!event || !type) return false;
      const id = toolId(event);
      let phase;
      if (type === 'tool.start' || type === 'tool.generating') {
        phase = { id: id || 'tool-' + (this.events.length + 1), type: 'tool', status: 'running', name: toolLabel(event), detail: detailFor(event) };
        this.byTool.set(phase.id, phase);
        this.events.push(phase);
      } else if (type === 'tool.progress') {
        phase = this.byTool.get(id) || this._newPhase(id, event);
        phase.status = 'progress'; phase.detail = detailFor(event) || phase.detail;
      } else if (type === 'tool.complete' || type === 'tool.result') {
        phase = this.byTool.get(id) || this._newPhase(id, event);
        phase.status = event.error || event.is_error ? 'error' : 'complete';
        phase.detail = detailFor(event) || phase.detail;
      } else if (type === 'thinking.delta' || type === 'reasoning.delta' || type === 'thinking' || type === 'reasoning') {
        phase = { id: 'thinking-' + (this.events.length + 1), type: 'thinking', status: 'complete', name: 'Thinking', detail: event.text || event.content || detailFor(event) };
        this.events.push(phase);
      } else if (type === 'agent.start' || type === 'agent.progress' || type === 'agent.complete' || type === 'agent.failed') {
        const agentId = String(event.run_id || event.id || 'agent-' + (this.events.length + 1));
        phase = this.byAgent.get(agentId);
        if (!phase) { phase = { id: agentId, type: 'agent', status: 'running', name: event.summary || 'Agent', detail: detailFor(event) }; this.byAgent.set(agentId, phase); this.events.push(phase); }
        phase.status = type === 'agent.failed' ? 'error' : type === 'agent.complete' ? 'complete' : type === 'agent.progress' ? 'progress' : 'running';
        phase.name = event.summary || phase.name;
        phase.detail = detailFor(event) || phase.detail;
      } else {
        return false;
      }
      this._renderPhase(phase);
      this.current.textContent = phase.status === 'complete' || phase.status === 'error' ? phase.name : (phase.name + ' · ' + statusText(phase.status));
      return true;
    }

    _newPhase(id, event) {
      const phase = { id: id || 'tool-' + (this.events.length + 1), type: 'tool', status: 'running', name: toolLabel(event), detail: detailFor(event) };
      this.byTool.set(phase.id, phase); this.events.push(phase); return phase;
    }

    _renderPhase(phase) {
      let row = this.trail.querySelector('[data-phase-id="' + CSS.escape(phase.id) + '"]');
      if (!row) {
        row = document.createElement('div'); row.className = 'lin-agent-phase'; row.dataset.phaseId = phase.id;
        row.innerHTML = '<button type="button" class="lin-agent-phase-toggle"><span class="lin-agent-phase-icon">·</span><span class="lin-agent-phase-label"></span><span class="lin-agent-phase-state"></span><span class="lin-agent-chevron">⌄</span></button><pre class="lin-agent-phase-detail"></pre>';
        row.querySelector('.lin-agent-phase-toggle').onclick = () => row.classList.toggle('expanded');
        this.trail.appendChild(row);
      }
      row.className = 'lin-agent-phase lin-agent-' + phase.status;
      row.querySelector('.lin-agent-phase-icon').textContent = phase.status === 'complete' ? '✓' : phase.status === 'error' ? '!' : '·';
      row.querySelector('.lin-agent-phase-label').textContent = phase.name;
      row.querySelector('.lin-agent-phase-state').textContent = statusText(phase.status);
      row.querySelector('.lin-agent-phase-detail').textContent = safeJson(phase.detail);
    }

    complete() {
      if (!this.root.isConnected) return;
      const history = document.createElement('div'); history.className = 'lin-agent-history';
      const doneCount = this.events.filter(e => e.type === 'tool' && e.status === 'complete').length;
      const summary = this.events.find(e => e.type === 'tool')?.name || 'Agent';
      history.innerHTML = '<button type="button" class="lin-agent-history-header" aria-expanded="false"><span class="lin-agent-mark">✦</span><span class="lin-agent-history-summary"></span><span class="lin-agent-history-count"></span><span class="lin-agent-chevron">⌄</span></button><div class="lin-agent-history-body"></div>';
      history.querySelector('.lin-agent-history-summary').textContent = summary;
      history.querySelector('.lin-agent-history-count').textContent = doneCount ? doneCount + ' Tool' : this.events.length + ' step';
      const body = history.querySelector('.lin-agent-history-body');
      this.events.forEach(e => {
        const row = document.createElement('div'); row.className = 'lin-agent-history-phase';
        row.innerHTML = '<button type="button"><span class="phase-icon"></span><span class="phase-label"></span><span class="phase-state"></span></button><pre></pre>';
        row.querySelector('.phase-icon').textContent = e.status === 'complete' ? '✓' : e.status === 'error' ? '!' : '·';
        row.querySelector('.phase-label').textContent = e.name;
        row.querySelector('.phase-state').textContent = statusText(e.status);
        row.querySelector('pre').textContent = safeJson(e.detail);
        row.querySelector('button').onclick = () => row.classList.toggle('expanded');
        body.appendChild(row);
      });
      const header = history.querySelector('.lin-agent-history-header');
      header.onclick = () => { const open = history.classList.toggle('expanded'); header.setAttribute('aria-expanded', String(open)); };
      this.root.replaceWith(history); this.root = history;
    }

    snapshot() { return { events: this.events }; }
  }

  class Turn {
    constructor(container) { this.container = container; this.currentText = null; this.activity = null; this.history = []; }

    createTextSegment() {
      const row = document.createElement('div'); row.className = 'msg lin lin-agent-text-segment';
      row.innerHTML = '<div class="msg-row">' + (typeof avatarHtml === 'function' ? avatarHtml('lin') : '<div class="msg-avatar">🐈</div>') + '<div class="bub"></div></div>';
      this.container.appendChild(row); this.currentText = row.querySelector('.bub'); return this.currentText;
    }

    appendText(delta) { if (!delta) return; if (!this.currentText) this.createTextSegment(); this.currentText.textContent += delta; this._scroll(); }
    thinking(text) { if (!text) return; if (!this.currentText) this.createTextSegment(); const row = this.currentText.closest('.msg'); let box = row && row.querySelector('.lin-agent-thinking'); if (!box && row) { const toggle = document.createElement('button'); toggle.type = 'button'; toggle.className = 'think-toggle'; toggle.textContent = '💭 查看思考過程'; toggle.onclick = () => toggleThink(toggle); box = document.createElement('div'); box.className = 'think-box lin-agent-thinking'; box.style.display = 'none'; row.insertBefore(toggle, row.querySelector('.msg-row')); row.insertBefore(box, row.querySelector('.msg-row')); } if (box) box.textContent += text; this._scroll(); }
    handleTimelineEvent(raw) { const event = unwrap(raw); if (!event || event.type === 'memory') return false; const status = String(event.status || '').toLowerCase(); const id = String(event.id || ''); const terminal = ['success', 'failed', 'skipped', 'not_executed', 'unknown'].includes(status); const failed = ['failed', 'unknown'].includes(status); const mapped = { ...event, type: terminal ? 'tool.complete' : this.activity?.byTool?.has(id) ? 'tool.progress' : 'tool.start', tool_id: id, name: event.display_name || event.name || event.type, summary: event.summary || event.reason, is_error: failed || undefined }; this.handleEvent(mapped); return true; }
    handleEvent(raw) { const event = unwrap(raw); const type = typeOf(event); if (!type) return; if (type === 'thinking.delta' || type === 'reasoning.delta' || type === 'thinking' || type === 'reasoning') { this.thinking(event.text || event.content || ''); return; } if (type === 'tool.start' || type === 'tool.generating' || type === 'agent.start') { this.currentText = null; if (!this.activity) this.activity = new Activity(this.container); } if (type.startsWith('tool.') || type.startsWith('agent.')) { if (!this.activity) this.activity = new Activity(this.container); this.activity.ingest(event); if (type === 'tool.complete' || type === 'tool.result' || type === 'agent.complete' || type === 'agent.failed') { if (this.activity.events.some(e => e.status === 'running' || e.status === 'progress')) return; this.history.push(this.activity.snapshot()); this.activity.complete(); this.activity = null; this.currentText = null; } this._scroll(); } }
    finish() { if (this.activity) { this.history.push(this.activity.snapshot()); this.activity.complete(); this.activity = null; } return this.snapshot(); }
    snapshot() { return this.history.length ? { activities: this.history.slice() } : null; }
    fail(text) { if (text) this.appendText(text); this.finish(); }
    _scroll() { if (typeof scrollDown === 'function') scrollDown(); else this.container.scrollTop = this.container.scrollHeight; }
  }

  window.AgentActivity = {
    create(container) { return new Turn(container); },
    mountHistory(container, snapshot) { (snapshot?.activities || []).forEach(item => { const a = new Activity(container); a.events = (item.events || []).map(e => ({ ...e })); a.events.forEach(e => { if (e.type === 'tool') a.byTool.set(String(e.id), e); if (e.type === 'agent') a.byAgent.set(String(e.id), e); a._renderPhase(e); }); a.complete(); }); return container; },
    unwrap,
  };
})();
