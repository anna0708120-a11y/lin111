/* Life System UI: readable Life Center with optional raw developer views. */
(function () {
  const modes = { dynamic: 'readable', context: 'readable', timeline: 'readable', audit: 'readable' };
  let data = { state: {}, context: {}, events: [], timeline: [], audit: [], device: {} };
  let refreshLastAt = 0;
  const refreshCooldownMs = 5000;

  const escapeHtml = (value) => String(value ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  const pretty = (value) => JSON.stringify(value ?? null, null, 2);
  const formatTime = (value) => {
    if (!value) return '—';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('zh-TW', { hour12: false });
  };
  const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  const getJson = async (path) => {
    const response = await fetch(AU + path, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  };
  const label = (map, value, fallback = '暂无数据') => map[value] || fallback;
  const locationLabel = (value) => label({ at_home: '在家', outside: '外出', unknown: '暂无数据' }, value);
  const status = (text, error = false) => {
    const el = document.getElementById('lifeRefreshStatus');
    if (el) { el.textContent = text; el.classList.toggle('life-error', error); }
  };
  const raw = (value) => `<pre class="life-context-json">${escapeHtml(pretty(value))}</pre>`;
  const empty = (text) => `<div class="life-empty">${escapeHtml(text)}</div>`;

  function renderDevice() {
    const el = document.getElementById('lifeDeviceSummary');
    if (!el) return;
    const state = data.state || {};
    const persistent = data.device.persistent || {};
    const cards = [
      ['location', '位置', state.location_state === 'unknown' || !state.location_state ? '暂无数据' : locationLabel(state.location_state), state.location_observed_at ? `最后位置事件：${formatTime(state.location_observed_at)}` : '尚未接入位置快捷指令'],
      ['mac', '电脑', persistent.mac?.message || (state.mac_state === 'unknown' ? '尚未接入' : label({ active: '使用中', idle: '闲置', locked: '已锁定' }, state.mac_state)), persistent.mac?.time ? `最后更新：${persistent.mac.time}` : '最后更新：—'],
      ['screentime', '屏幕使用', persistent.screentime?.message || (state.screen_activity === 'unknown' ? '尚未接入' : label({ low: '使用较少', moderate: '适度使用', high: '使用较多' }, state.screen_activity)), persistent.screentime?.time ? `最后更新：${persistent.screentime.time}` : '最后更新：—'],
      ['app', '手机与网络', persistent.app?.message || '暂无数据', persistent.app?.time ? `最后更新：${persistent.app.time}` : '尚未接入 iPhone 快捷指令'],
      ['weather', '天气', persistent.weather?.message || '暂无数据', persistent.weather?.time ? `最后更新：${persistent.weather.time}` : '最后更新：—'],
      ['calendar', '日程', state.current_schedule?.title ? `进行中：${state.current_schedule.title}` : state.next_schedule?.title ? `下一项：${state.next_schedule.title}` : '暂无日程', state.current_schedule?.start || state.next_schedule?.start ? `时间：${formatTime(state.current_schedule?.start || state.next_schedule?.start)}` : '最后更新：—'],
      ['conversation', '对话', label({ active: '正在交流', idle: '暂时安静', unknown: '暂无数据' }, state.conversation_state), state.last_user_activity_at ? `最后互动：${formatTime(state.last_user_activity_at)}` : '最后更新：—'],
    ];
    const icons = { location: '⌂', mac: '▣', screentime: '◷', app: '◌', weather: '☼', calendar: '□', conversation: '○' };
    el.innerHTML = cards.map(([type, title, message, meta]) => `<article class="life-device-item"><div class="life-device-icon">${icons[type]}</div><div class="life-device-label">${title}</div><div class="life-device-message">${escapeHtml(message)}</div><div class="life-device-time">${escapeHtml(meta)}</div></article>`).join('');
  }

  function renderDynamic() {
    const el = document.getElementById('lifeDynamicObservation');
    if (!el) return;
    const dynamic = data.context.dynamic || {};
    if (modes.dynamic === 'raw') { el.innerHTML = raw(dynamic); return; }
    const phone = dynamic.phone;
    if (!phone) { el.innerHTML = empty('暂无可用手机观察；尚未接入或最后观察已过期。'); return; }
    const items = [
      ['最近使用', phone.app_name || '暂无数据'],
      ['电量', phone.battery_level == null ? '暂无数据' : `${phone.battery_level}%`],
      ['充电状态', phone.battery_state || '暂无数据'],
      ['观察时间', formatTime(phone.observed_at)],
    ];
    el.innerHTML = `<div class="life-device-summary">${items.map(([title, message]) => `<div class="life-device-item"><div class="life-device-label">${title}</div><div class="life-device-message">${escapeHtml(message)}</div></div>`).join('')}</div>`;
  }

  function renderContext() {
    const el = document.getElementById('lifeContext');
    if (!el) return;
    if (modes.context === 'raw') { el.innerHTML = raw(data.context); return; }
    const state = data.context.stable || data.state || {};
    const facts = [
      ['位置', state.location_state === 'unknown' || !state.location_state ? '暂无数据' : locationLabel(state.location_state)],
      ['电脑', state.mac_state === 'unknown' || !state.mac_state ? '尚未接入' : label({ active: '使用中', idle: '闲置', locked: '已锁定' }, state.mac_state)],
      ['屏幕使用', state.screen_activity === 'unknown' || !state.screen_activity ? '尚未接入' : label({ low: '使用较少', moderate: '适度使用', high: '使用较多' }, state.screen_activity)],
      ['对话', label({ active: '正在交流', idle: '暂时安静', unknown: '暂无数据' }, state.conversation_state)],
      ['当前日程', state.current_schedule?.title || '暂无日程'],
      ['下一项日程', state.next_schedule?.title || '暂无日程'],
    ];
    el.innerHTML = `<div class="life-device-summary">${facts.map(([title, message]) => `<div class="life-device-item"><div class="life-device-label">${title}</div><div class="life-device-message">${escapeHtml(message)}</div></div>`).join('')}</div>`;
  }

  function eventText(event) {
    const map = {
      'location.returned_home': '回到家了', 'location.left_home': '离开家了',
      'mac.active': '电脑开始使用', 'mac.idle': '电脑进入闲置', 'mac.locked': '电脑已锁定', 'mac.unlocked': '电脑已解锁',
      'conversation.user_message': '你发来消息', 'conversation.lin_message': 'Lin 回复了消息',
      'conversation.idle_elapsed': '对话暂时安静', 'screentime.summary': '更新屏幕使用时间',
      'calendar.upcoming': '日程即将开始', 'phone.observed': '更新手机观察',
    };
    return map[event.event_type] || '记录了一项生活状态';
  }

  function renderTimeline() {
    const el = document.getElementById('lifeTimeline');
    if (!el) return;
    if (modes.timeline === 'raw') { el.innerHTML = raw(data.timeline); return; }
    if (!data.timeline.length) { el.innerHTML = empty('这一天还没有 Life 记录。'); return; }
    el.innerHTML = data.timeline.slice().reverse().map((event) => `<article class="life-event-row"><div class="life-event-time">${escapeHtml(event.time || formatTime(event.occurred_at))}</div><div class="life-event-dot"></div><div class="life-event-body"><div class="life-event-label">${escapeHtml(eventText(event))}</div><div class="life-event-payload">${escapeHtml(event.payload?.title || event.payload?.app_name || event.payload?.total_minutes != null ? String(event.payload.title || event.payload.app_name || `${event.payload.total_minutes} 分钟`) : '')}</div></div></article>`).join('');
  }

  async function renderAudit() {
    const el = document.getElementById('lifeAudit');
    if (!el) return;
    if (modes.audit === 'raw') { el.innerHTML = raw(data.audit); return; }
    if (!data.audit.length) { el.innerHTML = empty('目前没有 Life 自动处理记录。'); return; }
    const text = { candidate: '发现一个可处理的生活事件', policy: '已完成安全检查', decision: '已完成行动判断', outbox: '已写入待处理项目', action: '行动处理结果', tick: '系统巡检' };
    el.innerHTML = data.audit.slice().reverse().map((row) => `<article class="life-audit-row"><div class="life-audit-head"><strong>${escapeHtml(text[row.stage] || 'Life 记录')}</strong><span class="life-status">${escapeHtml(row.status || '完成')}</span></div><div class="life-audit-meta">${escapeHtml(formatTime(row.created_at))}</div><div class="life-audit-reason">${escapeHtml(row.reason || '—')}</div></article>`).join('');
  }

  function renderAll() { renderDevice(); renderDynamic(); renderContext(); renderTimeline(); renderAudit(); }

  window.setLifeMode = function (section, mode) {
    modes[section] = mode;
    document.querySelectorAll(`[data-life-toggle="${section}"] button`).forEach((button) => button.classList.toggle('active', button.textContent === (mode === 'raw' ? 'Raw' : '顯示')));
    renderAll();
  };

  async function refreshLife() {
    if (refreshInFlight) return refreshInFlight;
    const now = Date.now();
    if (now - refreshLastAt < refreshCooldownMs) return;
    refreshLastAt = now;
    refreshInFlight = (async () => {
    const input = document.getElementById('lifeTimelineDate');
    const date = input?.value || today();
    status('更新中…');
    try {
      try {
        await fetch(AU + '/life/context/refresh', { method: 'POST', headers: { Accept: 'application/json' } });
      } catch (_refreshError) {
        // Keep the last valid Life view available when providers are unavailable.
      }
      const [state, context, events, timeline, audit, device] = await Promise.all([
        getJson('/life/state'), getJson('/life/context'), getJson('/life/events?limit=50'),
        getJson(`/life/timeline?date=${encodeURIComponent(date)}`), getJson('/life/audit'), getJson('/events'),
      ]);
      data = { state: state.state || {}, context: context || {}, events: events.events || [], timeline: timeline.events || [], audit: audit.audit || [], device: device || {} };
      renderAll();
      status(`最后更新 ${new Date().toLocaleTimeString('zh-TW', { hour12: false })}`);
    } catch (error) {
      status('Life System 暂时无法读取', true);
    }
    })();
    try {
      return await refreshInFlight;
    } finally {
      refreshInFlight = null;
    }
  }

  window.refreshLife = refreshLife;
  window.initLifeView = function () {
    const input = document.getElementById('lifeTimelineDate');
    if (input && !input.value) input.value = today();
    refreshLife();
  };
})();
