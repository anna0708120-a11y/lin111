/**
 * Agent Activity Timeline —— 吸附在每則 Lin 回覆下方，顯示「AI 現在正在做什麼」。
 *
 * 定位（重寫後）：這不是 Developer Panel（不展示 Prompt/Backend/Parser 這種 debug 步驟），
 * 而是 Agent Activity Timeline —— 展示 Tool Runtime 正在/剛剛執行的動作
 * （Browser / Vision / Memory / 未來任何 Tool），核心是「正在做什麼」不是「內部怎麼實作」。
 *
 * 資料來源：app/agent/event_bus.py 的 Timeline，兩種形狀都吃：
 *   - 單一事件（即時 SSE，一次一個 event）：
 *     { version: 2, trace_id, event: { id, type, status, summary, summary_history, payload, reason, updated_at } }
 *   - 完整快照（歷史訊息回放，一次全部 events）：
 *     { version: 2, trace_id, step_count, duration_ms, events: { id: {...}, id2: {...} } }
 *
 * Timeline 本身不認識 memory/browser/vision 是什麼，只認識 id/type/status/summary，
 * 依 type 選 icon（ICONS_BY_TYPE），未知 type 一律 fallback 成通用 tool icon，
 * 不 hardcode 檢查任何具體領域字串。
 *
 * 收起時只佔一行：⚡ Agent · N steps · X.Xs ▸
 * 展開後逐行 Timeline node：✓/●/✕/○ + summary，running 狀態下 summary 用跑馬燈
 * （水平滑動）切換 summary_history 裡最新那幾句，不是直接替換文字。
 *
 * 更新方式：收到單一事件時，只更新該 event.id 對應的 DOM node，不整體重繪。
 */

// ---- Icon 集合：純 inline SVG，不用 emoji，依 status 決定圖示 ----
const AT_STATUS_ICONS = {
  success: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
  failed: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
  running: '<svg class="at-spin" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-9-9"/></svg>',
  skipped: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/></svg>',
  not_executed: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4" stroke-dasharray="2 2.4"/></svg>',
  unknown: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/></svg>',
};

// 收起狀態 Header 用的 icon（⚡ Agent）。
const AT_HEADER_ICON = '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>';
const AT_CHEVRON = '<svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>';

// type → icon：Timeline 不 hardcode 認識 memory/browser/vision，這裡只是「目前已知」的
// 幾種 type 對應圖示，未知 type 一律 fallback 成 AT_TYPE_ICONS.default，不拋錯、不特殊處理。
const AT_TYPE_ICONS = {
  memory: '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z"/></svg>',
  browser: '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><line x1="3" y1="12" x2="21" y2="12"/><path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18"/></svg>',
  vision: '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="2.5"/></svg>',
  planner: '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
  default: '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.32 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
};

const AT_AUTO_COLLAPSE_MS = 3000;
const AT_SUMMARY_ROTATE_MS = 1400; // 跑馬燈：同一個 running 節點多句 summary 之間的切換間隔

function atEscape(str) {
  const div = document.createElement('div');
  div.textContent = str == null ? '' : String(str);
  return div.innerHTML;
}

function atTypeIcon(type) {
  return AT_TYPE_ICONS[type] || AT_TYPE_ICONS.default;
}

function atOverallStatus(events) {
  const values = Object.values(events || {});
  if (values.some(e => e.status === 'failed')) return 'failed';
  if (values.some(e => e.status === 'running')) return 'running';
  return 'success';
}

function atHeaderText(events, stepCount, durationMs) {
  const overall = atOverallStatus(events);
  const stepLabel = `${stepCount} step${stepCount === 1 ? '' : 's'}`;
  const timeLabel = durationMs != null ? (durationMs / 1000).toFixed(1) + 's' : '';
  if (overall === 'running') return `Agent · ${stepLabel}${timeLabel ? ' · ' + timeLabel : ''}`;
  if (overall === 'failed') return `Agent · ${stepLabel} · Failed`;
  return `Agent · ${stepLabel}${timeLabel ? ' · ' + timeLabel : ''}`;
}

/**
 * 一個 ActivityTimeline 實例 = 一則 Lin 回覆訊息底下的 Timeline 區塊。
 * container：要插入的 DOM 節點（訊息氣泡下方）。
 */
class ActivityTimelineInstance {
  constructor(container) {
    this.container = container;
    this.expanded = false;
    this.userExpandedOnce = false; // 使用者展開過一次後，這則訊息就不再自動收合
    this.events = {};       // id -> event dict（局部更新用）
    this.order = [];        // id 第一次出現的真實時間順序，Timeline 節點永遠依此排列
    this.stepCount = 0;
    this.durationMs = null;
    this.collapseTimer = null;
    this.rotateTimers = {}; // id -> setInterval handle，跑馬燈用
    this._buildSkeleton();
  }

  _buildSkeleton() {
    const root = document.createElement('div');
    root.className = 'at-root at-collapsed';
    root.innerHTML = `
      <div class="at-header">
        <span class="at-header-icon">${AT_HEADER_ICON}</span>
        <span class="at-header-text">Agent</span>
        <span class="at-header-chevron">${AT_CHEVRON}</span>
      </div>
      <div class="at-body-wrap"><div class="at-body"></div></div>
    `;
    root.querySelector('.at-header').addEventListener('click', () => this.toggle());
    this.container.appendChild(root);
    this.rootEl = root;
    this.headerTextEl = root.querySelector('.at-header-text');
    this.headerIconEl = root.querySelector('.at-header-icon');
    this.bodyWrapEl = root.querySelector('.at-body-wrap');
    this.bodyEl = root.querySelector('.at-body');
  }

  toggle(force) {
    const next = typeof force === 'boolean' ? force : !this.expanded;
    if (next === this.expanded) return;
    this.expanded = next;
    if (next) this.userExpandedOnce = true;
    if (this.collapseTimer) { clearTimeout(this.collapseTimer); this.collapseTimer = null; }

    if (this.expanded) {
      this.rootEl.classList.remove('at-collapsed');
      this.rootEl.classList.add('at-expanded');
      this.bodyWrapEl.style.maxHeight = this.bodyWrapEl.scrollHeight + 'px';
    } else {
      this.rootEl.classList.remove('at-expanded');
      this.rootEl.classList.add('at-collapsed');
      this.bodyWrapEl.style.maxHeight = '0px';
    }
  }

  // ------------------------------------------------------------------
  // 即時串流：一次一個 event，只更新對應 id 的 DOM node（不整體重繪 body）。
  // ------------------------------------------------------------------
  ingest(payload) {
    if (!payload || typeof payload !== 'object') return;
    const event = payload.event;
    if (!event || !event.id) return;

    const isNew = !(event.id in this.events);
    this.events[event.id] = event;
    if (isNew) {
      this.order.push(event.id);
      this._renderHeader();
      this._renderNodeList(); // 新節點：body 結構要重排，走完整重繪一次
    } else {
      this._updateNode(event.id); // 舊節點狀態變化：只更新這一個 DOM 片段
      this._renderHeader();
    }

    if (this.expanded) this.bodyWrapEl.style.maxHeight = this.bodyWrapEl.scrollHeight + 'px';

    // 使用者展開過就不再自動收合，直到下一則新的 assistant message（=新的 instance）。
    if (!this.userExpandedOnce) this._scheduleAutoCollapse();
  }

  // ------------------------------------------------------------------
  // 歷史訊息一次性掛載：吃完整快照 {events, step_count, duration_ms}，不需要動畫。
  // ------------------------------------------------------------------
  mountStatic(payload) {
    if (!payload || typeof payload !== 'object') return;
    const events = payload.events || {};
    this.events = Object.assign({}, events);
    // 歷史快照沒有天然的到達順序，用 updated_at 還原真實發生時間（不是套用任何領域固定順序），
    // 這樣 Timeline 才能忠實反映每個 Tool 實際執行的時點，跟即時串流時的行為一致。
    this.order = Object.keys(this.events).sort(
      (a, b) => (this.events[a].updated_at || 0) - (this.events[b].updated_at || 0)
    );
    this.stepCount = payload.step_count != null ? payload.step_count : this.order.length;
    this.durationMs = payload.duration_ms != null ? payload.duration_ms : null;
    this._renderHeader();
    this._renderNodeList();
  }

  // 相容屬性：frontend.py 的 smsg(...) 呼叫依賴 currentDevTrace.lastPayload 取得
  // 「這則訊息完整的 trace 快照」存進 chatMemoryCache，供歷史回放用（mountStatic 吃的格式）。
  // 用 getter 動態組出，不需要每次 ingest() 額外維護一份快照。
  get lastPayload() {
    if (!this.order.length) return null;
    return {
      version: 2,
      step_count: this.stepCount,
      duration_ms: this.durationMs,
      events: Object.assign({}, this.events),
    };
  }

  _scheduleAutoCollapse() {
    if (this.collapseTimer) clearTimeout(this.collapseTimer);
    this.collapseTimer = setTimeout(() => {
      if (this.expanded && !this.userExpandedOnce) this.toggle(false);
    }, AT_AUTO_COLLAPSE_MS);
  }

  _renderHeader() {
    this.stepCount = this.order.length;
    const timestamps = Object.values(this.events).map(e => e.updated_at).filter(t => t != null);
    this.durationMs = timestamps.length > 1
      ? Math.round((Math.max(...timestamps) - Math.min(...timestamps)) * 1000)
      : (this.durationMs != null ? this.durationMs : 0);

    const overall = atOverallStatus(this.events);
    this.headerIconEl.className = 'at-header-icon at-status-' + overall;
    this.headerTextEl.textContent = atHeaderText(this.events, this.stepCount, this.durationMs);
  }

  // 完整重排節點清單（只在新增節點時呼叫，或歷史一次性掛載時呼叫）。
  // this.order 永遠是節點第一次出現的真實時間順序，這裡不做任何額外排序。
  _renderNodeList() {
    if (!this.order.length) this.order = Object.keys(this.events);
    const orderedIds = this.order;

    let html = '<div class="at-timeline">';
    orderedIds.forEach((id, i) => {
      html += this._renderNodeHtml(id, i === orderedIds.length - 1);
    });
    html += '</div>';
    this.bodyEl.innerHTML = html;

    orderedIds.forEach(id => this._startRotateIfRunning(id));
  }

  _renderNodeHtml(id, isLast) {
    const event = this.events[id] || {};
    const status = event.status || 'unknown';
    const icon = AT_STATUS_ICONS[status] || AT_STATUS_ICONS.unknown;
    const typeIcon = atTypeIcon(event.type);
    const text = this._currentSummaryText(event);

    return `
      <div class="at-node" data-node-id="${atEscape(id)}">
        <div class="at-node-rail">
          <span class="at-node-dot at-status-${status}">${icon}</span>
          ${isLast ? '' : '<span class="at-node-line"></span>'}
        </div>
        <div class="at-node-main">
          <div class="at-node-type-icon">${typeIcon}</div>
          <div class="at-node-summary-wrap"><span class="at-node-summary">${atEscape(text)}</span></div>
        </div>
      </div>`;
  }

  // 局部更新：只替換這一個 id 對應的 DOM 片段（icon/status class/summary 文字），
  // 不重新產生整個 body innerHTML，符合「收到 agent_event 不要整個重畫，只更新對應 id」。
  _updateNode(id) {
    const nodeEl = this.bodyEl.querySelector(`.at-node[data-node-id="${CSS.escape(id)}"]`);
    if (!nodeEl) { this._renderNodeList(); return; } // 找不到節點（理論上不會發生），保守全量重繪一次

    const event = this.events[id] || {};
    const status = event.status || 'unknown';
    const dotEl = nodeEl.querySelector('.at-node-dot');
    dotEl.className = 'at-node-dot at-status-' + status;
    dotEl.innerHTML = AT_STATUS_ICONS[status] || AT_STATUS_ICONS.unknown;

    const summaryEl = nodeEl.querySelector('.at-node-summary');
    summaryEl.textContent = this._currentSummaryText(event);

    this._startRotateIfRunning(id);
  }

  _currentSummaryText(event) {
    const history = event.summary_history;
    if (Array.isArray(history) && history.length) return history[history.length - 1];
    return event.summary || '';
  }

  // 跑馬燈：running 狀態且 summary_history 有多句時，水平滑動切換顯示最後幾句，
  // 不是直接 textContent 替換（模擬 Dynamic Island 的滑動切換手感）。
  _startRotateIfRunning(id) {
    if (this.rotateTimers[id]) { clearInterval(this.rotateTimers[id]); delete this.rotateTimers[id]; }

    const event = this.events[id];
    if (!event || event.status !== 'running') return;
    const history = event.summary_history;
    if (!Array.isArray(history) || history.length < 2) return;

    let idx = history.length - 1;
    const nodeEl = this.bodyEl.querySelector(`.at-node[data-node-id="${CSS.escape(id)}"]`);
    if (!nodeEl) return;
    const wrapEl = nodeEl.querySelector('.at-node-summary-wrap');
    const summaryEl = nodeEl.querySelector('.at-node-summary');
    if (!wrapEl || !summaryEl) return;

    this.rotateTimers[id] = setInterval(() => {
      // 節點狀態已經變化（不再 running，或已被移除），停止跑馬燈。
      const current = this.events[id];
      if (!current || current.status !== 'running') {
        clearInterval(this.rotateTimers[id]);
        delete this.rotateTimers[id];
        return;
      }
      idx = (idx + 1) % history.length;
      wrapEl.classList.add('at-rotate-out');
      setTimeout(() => {
        summaryEl.textContent = history[idx];
        wrapEl.classList.remove('at-rotate-out');
        wrapEl.classList.add('at-rotate-in');
        setTimeout(() => wrapEl.classList.remove('at-rotate-in'), 220);
      }, 160);
    }, AT_SUMMARY_ROTATE_MS);
  }
}

/**
 * 工廠方法集合：
 * - createForContainer(container): 即時串流訊息用，回傳一個 instance，之後用 instance.ingest(payload) 持續更新。
 * - mountHistory(container, payload): 歷史訊息一次性掛載（不需要動畫、不需要自動收合）。
 */
const ActivityTimeline = {
  createForContainer(container) {
    return new ActivityTimelineInstance(container);
  },
  mountHistory(container, payload) {
    if (!payload) return;
    const instance = new ActivityTimelineInstance(container);
    instance.mountStatic(payload);
    return instance;
  },
};

window.ActivityTimeline = ActivityTimeline;
// 舊名相容：frontend.py / chat_view.js 過渡期仍可能呼叫 window.DevTrace，
// 兩個全域變數指向同一份實作，避免這次改動要同步改所有呼叫點的變數名。
window.DevTrace = ActivityTimeline;
