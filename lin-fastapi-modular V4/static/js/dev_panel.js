/*
/*
 * Developer Console is the single UI Agent visualisation surface.
 * It renders a compact, clickable chat entry and the full /developer console
 * from the same event model. It has no dependency on chat message history.
 */
(function () {
  const STORAGE_KEY = 'lin_developer_events';
  const CHANNEL_NAME = 'lin-ui-agent';
  const MAX_EVENTS = 500;
  const channel = 'BroadcastChannel' in window ? new BroadcastChannel(CHANNEL_NAME) : null;

  function escapeHtml(value) {
    const node = document.createElement('div');
    node.textContent = value == null ? '' : String(value);
    return node.innerHTML;
  }

  function now() {
    return new Date().toISOString();
  }

  function loadEvents() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      return Array.isArray(parsed) ? parsed : [];
    } catch (_) {
      return [];
    }
  }

  function persist(event) {
    const events = loadEvents();
    events.push(event);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(events.slice(-MAX_EVENTS)));
  }

  function normalize(type, data) {
    const event = { id: Date.now() + '-' + Math.random().toString(16).slice(2), type, data: data || {}, at: now() };
    if (type === 'agent_event') {
      const agentEvent = event.data.event || {};
      event.status = agentEvent.status || 'unknown';
      event.label = agentEvent.id || 'agent_event';
      event.value = agentEvent.summary || agentEvent.reason || '';
      event.section = agentEvent.id === 'prompt' ? 'Prompt' : agentEvent.id === 'reasoning' ? 'Thinking' : ['memory_decision', 'parser', 'backend', 'database'].includes(agentEvent.id) ? 'Memory' : 'Event';
    } else if (type === 'reasoning') {
      event.section = 'Thinking'; event.label = 'reasoning'; event.value = event.data.content || ''; event.status = 'running';
    } else if (type === 'content') {
      event.section = 'Chat'; event.label = 'Streaming'; event.value = event.data.delta || ''; event.status = 'running';
    } else if (type === 'api_start') {
      event.section = 'Chat'; event.label = 'API Start'; event.value = event.data.model || 'watch'; event.status = 'running';
    } else if (type === 'mood') {
      event.section = 'Mood'; event.label = event.data.key || 'mood'; event.value = JSON.stringify(event.data.value); event.status = 'success';
    } else if (type === 'body_state') {
      event.section = 'Body State'; event.label = event.data.key || 'body_state'; event.value = JSON.stringify(event.data.value); event.status = 'success';
    } else if (type === 'done') {
      event.section = 'SSE'; event.label = 'done'; event.value = 'stream complete'; event.status = 'success';
    } else {
      event.section = 'Debug'; event.label = type; event.value = JSON.stringify(event.data); event.status = 'unknown';
    }
    return event;
  }

  function emit(type, data) {
    const event = normalize(type, data);
    persist(event);
    if (channel) channel.postMessage(event);
    window.dispatchEvent(new CustomEvent('lin:developer-event', { detail: event }));
    return event;
  }

  function createCompact(container) {
    const row = document.createElement('div');
    row.className = 'msg lin developer-chat-row';
    row.innerHTML = '<button class="developer-compact" type="button" title="Open Developer Console"><span class="developer-compact-title">Developer</span><span class="developer-compact-state">Starting</span><span class="developer-compact-count">0</span><span class="developer-compact-arrow">›</span></button>';
    const button = row.querySelector('.developer-compact');
    const state = row.querySelector('.developer-compact-state');
    const count = row.querySelector('.developer-compact-count');
    let total = 0;
    button.onclick = () => window.open('/developer', '_blank', 'noopener');
    container.appendChild(row);

    return {
      ingest(event) {
        total += 1;
        count.textContent = String(total);
        state.textContent = event.label === 'done' ? 'Done' : event.label || 'Streaming';
        button.classList.toggle('is-complete', event.status === 'success' || event.type === 'done');
      },
      complete() {
        state.textContent = 'Done';
        button.classList.add('is-complete');
      },
    };
  }

  function mountFull(root) {
    const sections = ['Chat', 'Thinking', 'Memory', 'Prompt', 'Mood', 'Body State', 'SSE', 'Event', 'Debug'];
    const lists = {};
    let paused = false;
    const statusEl = document.getElementById('stream-state');
    const badgeEl = document.getElementById('connection-badge');

    sections.forEach((name) => {
      const section = document.createElement('section');
      section.className = 'console-section';
      section.innerHTML = '<div class="section-header"><span class="section-title">' + name + '</span><span class="section-meta"><span class="count">0</span><span class="chevron">▼</span></span></div><div class="section-body"><div class="log-list"><div class="empty">Waiting...</div></div></div>';
      section.querySelector('.section-header').onclick = () => section.classList.toggle('collapsed');
      root.appendChild(section);
      lists[name] = section.querySelector('.log-list');
    });

    function append(event) {
      const list = lists[event.section] || lists.Debug;
      const empty = list.querySelector('.empty');
      if (empty) empty.remove();
      const row = document.createElement('div');
      row.className = 'log-entry ' + (event.status || '');
      row.innerHTML = '<span class="kind">' + escapeHtml(event.label) + '</span><span class="value">' + escapeHtml(event.value) + '</span>';
      list.appendChild(row);
      list.closest('.console-section').querySelector('.count').textContent = String(list.children.length);
      if (statusEl) statusEl.textContent = 'Streaming · ' + new Date(event.at).toLocaleTimeString();
      if (badgeEl) { badgeEl.className = 'status-badge live'; badgeEl.textContent = 'LIVE'; }
      if (!paused) window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    }

    loadEvents().forEach(append);
    const receive = (event) => append(event.detail || event.data);
    window.addEventListener('lin:developer-event', receive);
    if (channel) channel.onmessage = (event) => append(event.data);
    window.addEventListener('storage', (event) => {
      if (event.key === STORAGE_KEY && event.newValue) {
        const events = loadEvents();
        const latest = events[events.length - 1];
        if (latest) append(latest);
      }
    });

    const pauseButton = document.getElementById('pause-scroll');
    const resumeButton = document.getElementById('resume-scroll');
    if (pauseButton) pauseButton.onclick = () => { paused = true; pauseButton.disabled = true; resumeButton.disabled = false; if (statusEl) statusEl.textContent = 'Scroll paused'; };
    if (resumeButton) resumeButton.onclick = () => { paused = false; pauseButton.disabled = false; resumeButton.disabled = true; window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }); };
    const clearButton = document.getElementById('clear-log');
    if (clearButton) clearButton.onclick = () => { localStorage.removeItem(STORAGE_KEY); Object.values(lists).forEach((list) => { list.innerHTML = '<div class="empty">Waiting...</div>'; list.closest('.console-section').querySelector('.count').textContent = '0'; }); };
  }

  async function refreshState() {
    try {
      const [moodResponse, bodyResponse] = await Promise.all([fetch('/mood'), fetch('/intimacy/status')]);
      if (moodResponse.ok) {
        const mood = await moodResponse.json();
        Object.entries(mood.mood || {}).forEach(([key, value]) => emit('mood', { key, value }));
      }
      if (bodyResponse.ok) {
        const body = await bodyResponse.json();
        Object.entries(body.body_values || {}).forEach(([key, value]) => emit('body_state', { key, value }));
      }
    } catch (_) {
      // The stream remains usable when optional status endpoints are unavailable.
    }
  }

  window.DeveloperConsole = { emit, createCompact, mountFull, loadEvents, refreshState };
  window.publishDevEvent = emit;
})();
