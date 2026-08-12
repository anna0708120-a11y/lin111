/*
/*
 * AgentPanel is the only agent lifecycle UI.
 * It renders existing SSE and collector events without creating synthetic traces.
 */
(function () {
  const AUTO_COLLAPSE_MS = 2600;

  function normalizeStatus(status) {
    if (status === 'passed') return 'success';
    if (status === 'failed' || status === 'error') return 'error';
    if (['pending', 'running', 'success', 'skipped', 'not_executed'].includes(status)) return status;
    return 'pending';
  }

  function labelFor(event) {
    const id = String(event.id || event.type || '').toLowerCase();
    if (id === 'api_start') return 'API Request';
    if (id === 'prompt') return 'Prompt Building';
    if (id === 'reasoning') return 'Thinking';
    if (id === 'memory_decision') return 'Memory Decision';
    if (id === 'parser') return 'Memory Parser';
    if (id === 'backend') return 'Memory Write';
    if (id === 'database') return 'Database';
    if (id === 'body_state') return 'Body State';
    if (id === 'mood') return 'Mood';
    if (id === 'streaming' || id === 'content') return 'Response Streaming';
    if (id === 'done') return 'Response Complete';
    if (id.includes('search')) return 'Web Search';
    if (id.includes('calendar')) return 'Calendar';
    if (id.includes('github')) return 'GitHub';
    if (id.includes('voice') || id.includes('tts')) return 'Voice';
    if (id.includes('image') || id.includes('vision')) return 'Image';
    if (id.includes('tool')) return 'Tool Calling';
    return event.summary || event.type || event.id || 'Agent Event';
  }

  function detailFor(event) {
    if (event.summary) return event.summary;
    if (event.reason) return event.reason;
    if (event.payload && Object.keys(event.payload).length) return JSON.stringify(event.payload, null, 2);
    return '';
  }

  function fromSse(type, data) {
    if (type === 'tool_step_update') return data && data.event ? data.event : null;
    if (type === 'agent_event') return data && data.event ? data.event : null;
    if (type === 'api_start') return { id: 'api_start', status: 'running', summary: data.model || 'watch', payload: data };
    if (type === 'reasoning') return { id: 'reasoning', status: 'running', summary: data.content || '', payload: data };
    if (type === 'content') return { id: 'streaming', status: 'running', summary: data.delta || '', payload: data };
    if (type === 'body_state') return { id: 'body_state', status: 'success', summary: 'State updated', payload: data };
    if (type === 'mood') return { id: 'mood', status: 'success', summary: 'Mood updated', payload: data };
    if (type === 'done') return { id: 'done', status: 'success', summary: 'Completed', payload: data };
    if (type === 'error') return { id: 'api_error', status: 'failed', summary: data.message || 'Request failed', payload: data };
    return { id: type || 'agent_event', status: 'running', summary: '', payload: data || {} };
  }

  class AgentPanelInstance {
    constructor(container) {
      this.container = container;
      this.events = new Map();
      this.order = [];
      this.expanded = false;
      this.userToggled = false;
      this.collapseTimer = null;
      this.build();
    }

    build() {
      const root = document.createElement('div');
      root.className = 'agent-panel agent-panel-collapsed';
      root.innerHTML = '<button class="agent-panel-header" type="button" aria-expanded="false"><span class="agent-status agent-running"></span><span class="agent-panel-title">Agent</span><span class="agent-panel-summary">Preparing</span><span class="agent-panel-count">0</span><span class="agent-panel-chevron">⌄</span></button><div class="agent-panel-body"></div>';
      root.querySelector('.agent-panel-header').onclick = () => {
        this.userToggled = true;
        this.toggle(!this.expanded);
      };
      this.container.appendChild(root);
      this.root = root;
      this.header = root.querySelector('.agent-panel-header');
      this.status = root.querySelector('.agent-status');
      this.summary = root.querySelector('.agent-panel-summary');
      this.count = root.querySelector('.agent-panel-count');
      this.body = root.querySelector('.agent-panel-body');
    }

    toggle(expanded) {
      this.expanded = expanded;
      this.root.classList.toggle('agent-panel-expanded', expanded);
      this.root.classList.toggle('agent-panel-collapsed', !expanded);
      this.header.setAttribute('aria-expanded', String(expanded));
      if (this.collapseTimer) clearTimeout(this.collapseTimer);
    }

    autoCollapse() {
      if (this.userToggled || !this.expanded) return;
      if (this.collapseTimer) clearTimeout(this.collapseTimer);
      this.collapseTimer = setTimeout(() => this.toggle(false), AUTO_COLLAPSE_MS);
    }

    ingest(raw) {
      if (!raw) return;
      const event = { ...raw, id: String(raw.id || raw.type || 'agent_event'), status: normalizeStatus(raw.status) };
      const isNew = !this.events.has(event.id);
      this.events.set(event.id, event);
      if (isNew) this.order.push(event.id);
      this.render(event, isNew);
      if (event.status === 'running' && !this.userToggled) this.toggle(true);
      if (event.status === 'success' || event.status === 'error' || event.status === 'skipped' || event.status === 'not_executed') this.autoCollapse();
    }

    render(latest, isNew) {
      this.status.className = 'agent-status agent-' + latest.status;
      this.summary.textContent = labelFor(latest) + (latest.summary ? ' · ' + latest.summary : '');
      this.count.textContent = String(this.order.length);
      if (isNew) {
        const row = document.createElement('div');
        row.className = 'agent-step agent-' + latest.status;
        row.dataset.eventId = latest.id;
        row.innerHTML = '<button class="agent-step-header" type="button"><span class="agent-step-dot"></span><span class="agent-step-label"></span><span class="agent-step-state"></span><span class="agent-step-chevron">⌄</span></button><pre class="agent-step-detail"></pre>';
        row.querySelector('.agent-step-header').onclick = () => row.classList.toggle('agent-step-expanded');
        this.body.appendChild(row);
      }
      const row = this.body.querySelector('[data-event-id="' + CSS.escape(latest.id) + '"]');
      if (!row) return;
      row.className = 'agent-step agent-' + latest.status;
      row.querySelector('.agent-step-label').textContent = labelFor(latest);
      const stateLabels = {pending: 'Pending', running: 'Running', success: 'Success', error: 'Failed', skipped: 'Skipped', not_executed: 'Not_executed'};
      row.querySelector('.agent-step-state').textContent = stateLabels[latest.status] || latest.status;
      row.querySelector('.agent-step-detail').textContent = detailFor(latest);
    }

    complete() {
      this.ingest({ id: 'done', status: 'success', summary: 'Completed' });
    }

    snapshot() {
      return { events: Object.fromEntries(this.events.entries()) };
    }

    mountSnapshot(snapshot) {
      const events = snapshot && snapshot.events ? snapshot.events : {};
      Object.values(events)
        .sort((a, b) => (a.updated_at || 0) - (b.updated_at || 0))
        .forEach((event) => this.ingest(event));
      this.toggle(false);
    }
  }

  window.AgentPanel = {
    create(container) { return new AgentPanelInstance(container); },
    mountHistory(container, snapshot) {
      const instance = new AgentPanelInstance(container);
      instance.mountSnapshot(snapshot);
      return instance;
    },
    fromSse,
  };
})();
