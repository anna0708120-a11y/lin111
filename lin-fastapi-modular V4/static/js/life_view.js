/* Life System UI: read-only state, timeline, candidate and audit visibility. */
(function () {
  const root = () => document.getElementById('lifeUi');
  const stateValue = (value, fallback = '未知') => {
    if (value === null || value === undefined || value === '') return fallback;
    return String(value);
  };
  const escapeHtml = (value) => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
  const pretty = (value) => {
    if (value === null || value === undefined || value === '') return '—';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  };
  const formatTime = (value) => {
    if (!value) return '—';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('zh-TW', { hour12: false });
  };
  const locationLabel = (value) => ({
    at_home: '在家',
    outside: '外出',
    unknown: '未知',
  })[value] || stateValue(value);
  const today = () => {
    const now = new Date();
    const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  };

  async function getJson(path) {
    const response = await fetch(AU + path, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  }

  function setStatus(text, error = false) {
    const el = document.getElementById('lifeRefreshStatus');
    if (!el) return;
    el.textContent = text;
    el.classList.toggle('life-error', error);
  }

  function renderState(state) {
    const values = {
      location: locationLabel(state.location_state),
      mac: stateValue(state.mac_state),
      charging: state.mac_charging === true ? '充電中' : state.mac_charging === false ? '未充電' : '未知',
      screen: stateValue(state.screen_activity),
      conversation: stateValue(state.conversation_state),
      current: state.current_schedule ? pretty(state.current_schedule) : '無',
      next: state.next_schedule ? pretty(state.next_schedule) : '無',
      activity: formatTime(state.last_user_activity_at || state.last_conversation_at),
    };
    Object.entries(values).forEach(([key, value]) => {
      const el = document.querySelector(`[data-life-state="${key}"]`);
      if (el) el.textContent = value;
    });
    const observed = document.querySelector('[data-life-state="location-observed"]');
    if (observed) {
      observed.textContent = state.location_observed_at
        ? `最後位置事件：${formatTime(state.location_observed_at)}`
        : '等待快捷指令位置事件';
    }
    const updated = document.getElementById('lifeStateUpdated');
    if (updated) updated.textContent = state.updated_at ? `更新於 ${formatTime(state.updated_at)}` : '尚無持久化狀態';
  }

  function payloadSummary(payload) {
    if (!payload || typeof payload !== 'object') return '';
    const preferred = ['label', 'app_name', 'battery', 'battery_level', 'total_minutes', 'note'];
    const bits = preferred.filter((key) => payload[key] !== undefined && payload[key] !== null && payload[key] !== '')
      .map((key) => `${key}: ${payload[key]}`);
    return bits.length ? bits.join(' · ') : '';
  }

  function renderTimeline(events) {
    const el = document.getElementById('lifeTimeline');
    if (!el) return;
    if (!events.length) {
      el.innerHTML = '<div class="es">這一天還沒有 Life Event</div>';
      return;
    }
    el.innerHTML = events.slice().reverse().map((event) => `
      <article class="life-event-row">
        <div class="life-event-time">${escapeHtml(event.time || formatTime(event.occurred_at))}</div>
        <div class="life-event-dot"></div>
        <div class="life-event-body">
          <div class="life-event-label">${escapeHtml(event.label || event.event_type || 'Life Event')}</div>
          <div class="life-event-type">${escapeHtml(event.event_type || '')}</div>
          <div class="life-event-payload">${escapeHtml(payloadSummary(event.payload) || pretty(event.payload || ''))}</div>
        </div>
      </article>`).join('');
  }

  async function renderAudit(rows) {
    const el = document.getElementById('lifeAudit');
    if (!el) return;
    if (!rows.length) {
      el.innerHTML = '<div class="es">目前沒有 Candidate / Action / Audit 記錄</div>';
      return;
    }
    const ids = [...new Set(rows.map((row) => row.candidate_id).filter(Boolean))];
    const candidates = await Promise.all(ids.map(async (id) => {
      try { return await getJson(`/life/candidates/${encodeURIComponent(id)}`); } catch (_) { return { candidate: null }; }
    }));
    const byId = Object.fromEntries(candidates.map((item) => [item.candidate?.candidate_id, item.candidate]));
    el.innerHTML = rows.slice().reverse().map((row) => {
      const candidate = byId[row.candidate_id];
      const candidateText = candidate
        ? `${stateValue(candidate.status)} · ${stateValue(candidate.decision, '尚未決策')}`
        : 'Candidate 未找到';
      return `
        <article class="life-audit-row">
          <div class="life-audit-head"><strong>${escapeHtml(row.stage || 'audit')}</strong><span class="life-status">${escapeHtml(row.status || 'unknown')}</span></div>
          <div class="life-audit-meta">${escapeHtml(formatTime(row.created_at))} · ${escapeHtml(row.candidate_id || '無 candidate')}</div>
          <div class="life-audit-reason">${escapeHtml(row.reason || '—')}</div>
          <div class="life-audit-candidate">Candidate：${escapeHtml(candidateText)}</div>
        </article>`;
    }).join('');
  }

  function renderDynamic(context) {
    const el = document.getElementById('lifeDynamicObservation');
    if (!el) return;
    const dynamic = context.dynamic || {};
    const phone = dynamic.phone;
    if (!phone) {
      const phoneEvents = (dynamic.recent_events || []).filter((event) => event.event_type === 'phone.observed');
      if (!phoneEvents.length) {
        el.innerHTML = '<div class="life-observation">目前沒有可用的 Dynamic Observation</div>';
        return;
      }
      const latest = phoneEvents[phoneEvents.length - 1];
      el.innerHTML = `<div class="life-observation life-observation-stale">最新 phone observation 已過期，不會被 Lin 描述為目前狀態。</div><div class="life-observation-meta">source: ${escapeHtml((latest.payload || {}).observation_source || latest.source || 'unknown')} · observed: ${escapeHtml(formatTime(latest.occurred_at))} · confidence: ${escapeHtml(latest.confidence)}</div>`;
      return;
    }
    const lines = [
      `App: ${phone.app_name || '未提供'}`,
      `Battery: ${phone.battery_level ?? '未提供'}${phone.battery_level != null ? '%' : ''}`,
      `State: ${phone.battery_state || '未提供'}`,
    ];
    el.innerHTML = `<div class="life-observation">${escapeHtml(lines.join('\n'))}</div><div class="life-observation-meta">source: ${escapeHtml(phone.source)} · confidence: ${escapeHtml(phone.confidence)} · age: ${escapeHtml(phone.age_minutes)} min · fresh: ${escapeHtml(phone.fresh)} · current claim: ${escapeHtml(phone.current_claim_allowed)} · proactive use: ${escapeHtml(phone.usable_for_proactive_action)}</div>`;
  }

  function renderContext(context) {
    const el = document.getElementById('lifeContext');
    if (!el) return;
    const stable = context.stable || context.state || {};
    const dynamic = context.dynamic || {};
    const recent = dynamic.recent_events || context.recent_events || [];
    el.innerHTML = `<div class="life-context-block"><div class="life-context-title">Stable Life State</div><pre class="life-context-json">${escapeHtml(pretty(stable))}</pre></div><div class="life-context-block"><div class="life-context-title">Dynamic Read Model</div><pre class="life-context-json">${escapeHtml(pretty(dynamic))}</pre></div><div class="life-context-block"><div class="life-context-title">Recent Life Events (${recent.length})</div><pre class="life-context-json">${escapeHtml(pretty(recent))}</pre></div>`;
  }

  async function refreshLife() {
    const dateInput = document.getElementById('lifeTimelineDate');
    const date = dateInput?.value || today();
    setStatus('更新中…');
    try {
      const [stateData, contextData, eventData, timelineData, auditData] = await Promise.all([
        getJson('/life/state'),
        getJson('/life/context'),
        getJson('/life/events?limit=50'),
        getJson(`/life/timeline?date=${encodeURIComponent(date)}`),
        getJson('/life/audit'),
      ]);
      renderState(stateData.state || {});
      renderDynamic(contextData);
      renderContext({ ...contextData, dynamic: { ...(contextData.dynamic || {}), recent_events: (eventData.events || contextData.dynamic?.recent_events || []) } });
      renderTimeline(timelineData.events || []);
      await renderAudit(auditData.audit || []);
      setStatus(`最後更新 ${new Date().toLocaleTimeString('zh-TW', { hour12: false })}`);
    } catch (error) {
      setStatus('Life System 暫時無法讀取', true);
      const timeline = document.getElementById('lifeTimeline');
      if (timeline) timeline.innerHTML = `<div class="es life-error">${escapeHtml(error.message)}</div>`;
    }
  }

  window.refreshLife = refreshLife;
  window.initLifeView = function () {
    const input = document.getElementById('lifeTimelineDate');
    if (input && !input.value) input.value = today();
    refreshLife();
  };
})();
