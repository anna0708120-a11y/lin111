/* Mine-only diagnostic panel fed by real Lin SSE events. */
(function () {
  const CORE = [
    ['api_start', 'API Request'], ['prompt', 'Prompt Building'], ['reasoning', 'Thinking'],
    ['memory_decision', 'Memory Decision'], ['parser', 'Memory Parser'], ['backend', 'Memory Write'], ['database', 'Database']
  ];
  const AGENT = [
    ['tool_calling', 'Tool Calling'], ['backend_emitted', 'Backend emitted'], ['sse_received', 'SSE received'],
    ['sse_parsed', 'SSE parsed'], ['tool_step_update', 'tool_step_update'], ['agent_ingest', 'AgentPanel ingest'],
    ['hermes_tool', 'Hermes Tool'], ['tool_progress', 'Tool Progress'], ['tool_complete', 'Tool Complete'], ['agent_ui_rendered', 'Agent UI rendered']
  ];
  const TERMINAL = new Set(['success', 'failed', 'error', 'skipped', 'not_executed', 'unknown']);
  const state = { core: new Map(), agent: new Map(), rawEvents: [], errors: [], expanded: false };
  let root = null;

  function status(value) {
    if (value === 'success' || value === 'passed') return 'success';
    if (value === 'failed' || value === 'error') return 'error';
    if (value === 'skipped' || value === 'not_executed') return value;
    if (value === 'running' || value === 'pending') return 'running';
    return 'unknown';
  }
  function mark(value) { return value === 'success' ? '✓' : value === 'error' ? '✕' : value === 'running' ? '…' : '—'; }
  function raw(type, data) { return 'event: ' + type + '\ndata: ' + JSON.stringify(data, null, 2); }
  function set(map, key, value, detail) { map.set(key, { status: status(value), detail: detail || '' }); render(); }
  function addRaw(type, data) { state.rawEvents.unshift(raw(type, data)); state.rawEvents = state.rawEvents.slice(0, 30); render(); }
  function addError(message, payload) { state.errors.unshift({ message: String(message), payload: payload ? JSON.stringify(payload, null, 2) : '' }); state.errors = state.errors.slice(0, 20); render(); }

  function row(item, map) {
    const current = map.get(item[0]) || { status: 'unknown', detail: '' };
    return '<div class="lin-debug-row lin-debug-' + current.status + '"><span>' + item[1] + '</span><b title="' + current.status + '">' + mark(current.status) + '</b></div>' + (current.detail ? '<pre class="lin-debug-detail">' + escapeHtml(current.detail) + '</pre>' : '');
  }
  function escapeHtml(value) { return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function section(title, key, body) { return '<section class="lin-debug-section ' + (state[key] ? 'is-open' : '') + '"><button type="button" class="lin-debug-section-title" data-section="' + key + '"><span>' + title + '</span><span>⌄</span></button><div class="lin-debug-section-body">' + body + '</div></section>'; }

  function render() {
    if (!root) return;
    const errors = state.errors.length ? state.errors.map(e => '<div class="lin-debug-error"><b>✕ ' + escapeHtml(e.message) + '</b>' + (e.payload ? '<pre>' + escapeHtml(e.payload) + '</pre>' : '') + '</div>').join('') : '<div class="lin-debug-empty">— None</div>';
    const raws = state.rawEvents.length ? state.rawEvents.map(e => '<pre class="lin-debug-raw">' + escapeHtml(e) + '</pre>').join('') : '<div class="lin-debug-empty">— No raw events</div>';
    const body = section('Core Pipeline', 'coreOpen', CORE.map(item => row(item, state.core)).join('')) +
      section('Agent / Tool Pipeline', 'agentOpen', AGENT.map(item => row(item, state.agent)).join('')) +
      section('Raw Events', 'rawOpen', raws) + section('Errors', 'errorsOpen', errors);
    const errorCount = state.errors.length;
    root.innerHTML = '<button type="button" class="lin-debug-header" aria-expanded="' + state.expanded + '"><span>AGENT DEBUG</span><b>' + (errorCount ? '✕ · ' + errorCount + ' errors' : '✓') + '</b><span>⌄</span></button><div class="lin-debug-body">' + body + '</div>';
    root.classList.toggle('is-open', state.expanded);
    root.querySelector('.lin-debug-header').onclick = () => { state.expanded = !state.expanded; render(); };
    root.querySelectorAll('[data-section]').forEach(btn => { btn.onclick = () => { state[btn.dataset.section] = !state[btn.dataset.section]; render(); }; });
  }

  function recordSse(type, data) {
    addRaw(type, data);
    if (type === 'model') { set(state.core, 'prompt', 'success'); return; }
    if (type === 'done') { set(state.core, 'api_start', 'success'); return; }
    if (type === 'reasoning') { set(state.core, 'reasoning', data?.content ? 'success' : 'skipped', data?.content || ''); return; }
    if (type === 'text_delta' || type === 'content' || type === 'body_state') return;
    if (type === 'tool_step_update') {
      const event = data && data.event;
      if (!event) { set(state.agent, 'sse_received', 'success'); set(state.agent, 'sse_parsed', 'error'); addError('tool_step_update missing event envelope', data); return; }
      if (event.type === 'memory') { recordCore(event.id, event.status, event.summary || event.reason); return; }
      set(state.agent, 'sse_received', 'success'); set(state.agent, 'sse_parsed', 'success'); set(state.agent, 'tool_step_update', 'success');
      set(state.agent, 'backend_emitted', 'success'); set(state.agent, 'hermes_tool', 'success');
      const s = status(event.status); const detail = event.summary || event.reason || '';
      if (s === 'running') { set(state.agent, 'tool_calling', 'success'); set(state.agent, 'tool_progress', 'success', detail); }
      if (TERMINAL.has(String(event.status))) { set(state.agent, 'tool_complete', s === 'error' ? 'error' : 'success', detail); }
    } else if (type === 'agent_event') {
      set(state.agent, 'sse_received', 'success'); set(state.agent, 'sse_parsed', 'success');
    } else if (type === 'error') { set(state.core, 'api_start', 'error', data?.message || 'SSE error'); addError(data?.message || 'SSE error', data); }
    else addError('Unknown Event: ' + type, data);
    render();
  }
  function recordCore(id, value, detail) { if (CORE.some(item => item[0] === id)) set(state.core, id, value, detail); }
  function recordAgentIngest(ok, detail) { set(state.agent, 'agent_ingest', ok ? 'success' : 'error', detail); }
  function rendered(ok) { set(state.agent, 'agent_ui_rendered', ok ? 'success' : 'error'); }
  function mount(container) { root = container; render(); }

  function snapshot() { return { core: Object.fromEntries(state.core), agent: Object.fromEntries(state.agent), rawEvents: state.rawEvents.slice(), errors: state.errors.slice() }; }
  window.LinAgentDebug = { mount, recordSse, recordCore, recordAgentIngest, rendered, addError, snapshot };
})();
