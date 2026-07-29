/**
 * Developer Trace —— 吸附在每則 Lin 回覆下方的開發者追蹤區塊。
 *
 * 定位：不是固定右下角的浮動 widget，而是聊天訊息的一部分。
 * 每則 Lin 回覆自帶一個 DevTrace 實例，翻歷史時該回覆當時的 trace 一起顯示。
 *
 * 資料來源統一是 message.trace（TraceCollector.export() 的版本化 payload），
 * 不區分即時訊息（SSE devtrace）或歷史訊息（DB 讀回的 m.trace）——
 * 兩條路徑最後都呼叫 DevTrace.mount(container, payload)。
 *
 * 可擴展設計（registry，不寫死 section 清單）：
 *   DevTrace.registerSection('mood', { title: 'Mood Engine', renderDetail(section){...} })
 *   之後 Tool Calling / API / Vector Search / Planner / Workflow 都用這个方式加，
 *   不需要改这个文件的核心渲染/展開/Timeline逻辑。
 */

// ---- 統一 Icon 集合（不用 emoji，纯 inline SVG，走同一套 stroke 风格，接近 Lucide/Heroicons）----
const DT_ICONS = {
  passed: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
  failed: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
  waiting: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/></svg>',
  running: '<svg class="dt-spin" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-9-9"/></svg>',
  skipped: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/></svg>',
  not_executed: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9" stroke-dasharray="2.5 3"/></svg>',
  unknown: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="12.5"/><circle cx="12" cy="16" r="0.6" fill="currentColor" stroke="none"/></svg>',
  chevron: '<svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>',
  dev: '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
};

const DT_STATUS_LABEL = {
  passed: 'OK', failed: 'Failed', waiting: 'Waiting',
  running: 'Running', skipped: 'Skipped', not_executed: '—', unknown: 'Unknown',
};

const DT_PIPELINE_ORDER = ['prompt', 'reasoning', 'memory_decision', 'parser', 'backend', 'database'];

const DT_SECTION_META = {
  prompt: { title: 'Prompt' },
  reasoning: { title: 'Reasoning' },
  memory_decision: { title: 'Decision' },
  parser: { title: 'Parser' },
  backend: { title: 'Backend' },
  database: { title: 'Database' },
  mood: { title: 'Mood Engine' },
  tool: { title: 'Tool Calling' },
  api: { title: 'API' },
};

const DT_CUSTOM_RENDERERS = {};
const DT_AUTO_COLLAPSE_MS = 3000;

function dtRegisterSection(key, { title, renderDetail } = {}) {
  if (title) DT_SECTION_META[key] = Object.assign({}, DT_SECTION_META[key], { title });
  if (typeof renderDetail === 'function') DT_CUSTOM_RENDERERS[key] = renderDetail;
}

function dtEscape(str) {
  const div = document.createElement('div');
  div.textContent = str == null ? '' : String(str);
  return div.innerHTML;
}

function dtOverallStatus(sections) {
  const values = Object.values(sections || {});
  if (values.some(s => s.status === 'failed')) return 'failed';
  if (values.some(s => s.status === 'waiting' || s.status === 'running')) return 'waiting';
  if (values.length > 0 && values.every(s => s.status === 'passed' || s.status === 'skipped' || s.status === 'not_executed')) return 'passed';
  return 'unknown';
}

function dtSummaryText(sections) {
  const failedEntry = Object.entries(sections).find(([, v]) => v.status === 'failed');
  if (failedEntry) {
    const [key, val] = failedEntry;
    const title = (DT_SECTION_META[key] && DT_SECTION_META[key].title) || key;
    return `${title} Failed${val.reason ? ' · ' + val.reason : ''}`;
  }
  const dbEntry = sections.database;
  const backendEntry = sections.backend;
  if (dbEntry && dbEntry.status === 'passed') return 'Memory Saved';
  if (backendEntry && backendEntry.status === 'not_executed') return 'Memory · Nothing to save';
  const overall = dtOverallStatus(sections);
  if (overall === 'passed') return 'Memory Pipeline · OK';
  if (overall === 'waiting') return 'Memory Pipeline · Running...';
  return 'Developer Trace';
}

/**
 * 一個 DevTrace 實例 = 一則 Lin 回覆訊息底下的 Developer 區塊。
 * container：要插入的 DOM 節點（訊息氣泡下方）。
 */
class DevTraceInstance {
  constructor(container) {
    this.container = container;
    this.expanded = false;
    this.sectionState = {};
    this.lastPayload = null;
    this.collapseTimer = null;
    this._buildSkeleton();
  }

  _buildSkeleton() {
    const root = document.createElement('div');
    root.className = 'dt-root dt-collapsed';
    root.innerHTML = `
      <div class="dt-summary">
        <span class="dt-summary-icon">${DT_ICONS.dev}</span>
        <span class="dt-summary-text">Developer</span>
        <span class="dt-summary-chevron">${DT_ICONS.chevron}</span>
      </div>
      <div class="dt-body-wrap"><div class="dt-body"></div></div>
    `;
    root.querySelector('.dt-summary').addEventListener('click', () => this.toggle());
    this.container.appendChild(root);
    this.rootEl = root;
    this.summaryTextEl = root.querySelector('.dt-summary-text');
    this.summaryIconEl = root.querySelector('.dt-summary-icon');
    this.bodyWrapEl = root.querySelector('.dt-body-wrap');
    this.bodyEl = root.querySelector('.dt-body');
  }

  toggle(force) {
    const next = typeof force === 'boolean' ? force : !this.expanded;
    if (next === this.expanded) return;
    this.expanded = next;
    if (this.collapseTimer) { clearTimeout(this.collapseTimer); this.collapseTimer = null; }

    if (this.expanded) {
      this.rootEl.classList.remove('dt-collapsed');
      this.rootEl.classList.add('dt-expanded');
      // 高度 + opacity + translateY 動畫：先量出目標高度，再從 0 動畫到目標高度。
      this.bodyWrapEl.style.maxHeight = this.bodyWrapEl.scrollHeight + 'px';
    } else {
      this.rootEl.classList.remove('dt-expanded');
      this.rootEl.classList.add('dt-collapsed');
      this.bodyWrapEl.style.maxHeight = '0px';
    }
  }

  ingest(payload) {
    if (!payload || typeof payload !== 'object') return;
    this.lastPayload = payload;
    if (payload.version !== 1) {
      console.warn('[DevTrace] 未知 devtrace version:', payload.version);
    }
    this._renderSummary(payload);
    this._renderBody(payload);

    // 展開中的話，body 內容變了要重新量高度，避免動畫卡住。
    if (this.expanded) {
      this.bodyWrapEl.style.maxHeight = this.bodyWrapEl.scrollHeight + 'px';
    }

    this._scheduleAutoCollapse();
  }

  // 從歷史訊息直接掛載，不需要動畫效果、也不需要自動收合（本來就是靜態資料）。
  mountStatic(payload) {
    if (!payload || typeof payload !== 'object') return;
    this.lastPayload = payload;
    this._renderSummary(payload);
    this._renderBody(payload);
  }

  _scheduleAutoCollapse() {
    if (this.collapseTimer) clearTimeout(this.collapseTimer);
    this.collapseTimer = setTimeout(() => {
      if (this.expanded) this.toggle(false);
    }, DT_AUTO_COLLAPSE_MS);
  }

  _renderSummary(payload) {
    const sections = payload.sections || {};
    const overall = dtOverallStatus(sections);
    this.summaryIconEl.className = 'dt-summary-icon dt-status-' + overall;
    this.summaryIconEl.innerHTML = DT_ICONS[overall] || DT_ICONS.unknown;
    this.summaryTextEl.textContent = dtSummaryText(sections);
  }

  _renderBody(payload) {
    const sections = payload.sections || {};
    const keys = Object.keys(sections);
    const ordered = [
      ...DT_PIPELINE_ORDER.filter(k => keys.includes(k)),
      ...keys.filter(k => !DT_PIPELINE_ORDER.includes(k)),
    ];

    let html = `<div class="dt-meta">${dtEscape(payload.trace_id || '')} · ${payload.duration_ms != null ? payload.duration_ms + 'ms' : ''}</div>`;
    html += '<div class="dt-timeline">';

    ordered.forEach((key, i) => {
      const section = sections[key];
      const meta = DT_SECTION_META[key] || {};
      const title = meta.title || key;
      const status = section.status || 'unknown';
      const isOpen = !!(this.sectionState[key] && this.sectionState[key].expanded);
      const isLast = i === ordered.length - 1;

      html += `
        <div class="dt-node" data-section="${dtEscape(key)}">
          <div class="dt-node-rail">
            <span class="dt-node-dot dt-status-${status}">${DT_ICONS[status] || DT_ICONS.unknown}</span>
            ${isLast ? '' : '<span class="dt-node-line"></span>'}
          </div>
          <div class="dt-node-main">
            <div class="dt-node-head" data-toggle-section="${dtEscape(key)}">
              <span class="dt-node-title">${dtEscape(title)}</span>
              <span class="dt-node-status dt-status-${status}">${DT_STATUS_LABEL[status] || status}</span>
              <span class="dt-node-chevron ${isOpen ? 'dt-open' : ''}">${DT_ICONS.chevron}</span>
            </div>
            <div class="dt-node-detail" style="${isOpen ? '' : 'display:none;'}">${isOpen ? this._renderSectionDetail(key, section) : ''}</div>
          </div>
        </div>`;
    });

    html += '</div>';
    this.bodyEl.innerHTML = html;

    // Section 展開/收合：用事件委派綁在 body 上，重畫後不需要重新逐一綁定。
    this.bodyEl.querySelectorAll('[data-toggle-section]').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        this._toggleSection(el.getAttribute('data-toggle-section'));
      });
    });
  }

  _toggleSection(key) {
    if (!this.sectionState[key]) this.sectionState[key] = { expanded: false };
    this.sectionState[key].expanded = !this.sectionState[key].expanded;
    if (this.lastPayload) this._renderBody(this.lastPayload);
    if (this.expanded) this.bodyWrapEl.style.maxHeight = this.bodyWrapEl.scrollHeight + 'px';
  }

  _renderSectionDetail(key, section) {
    if (DT_CUSTOM_RENDERERS[key]) {
      try { return DT_CUSTOM_RENDERERS[key](section); }
      catch (e) { console.error('[DevTrace] custom renderer error:', key, e); }
    }
    let html = '';
    if (section.reason) {
      html += `<div class="dt-reason">${dtEscape(section.reason)}</div>`;
    }
    const data = section.data || {};
    const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined && v !== '');
    if (entries.length === 0 && !section.reason) {
      return html + '<div class="dt-empty">No data.</div>';
    }
    html += entries.map(([k, v]) => {
      if (k === 'reasoning_text' && typeof v === 'string') {
        return `<div class="dt-kv-block"><span class="dt-kv-key">${dtEscape(k)}</span><pre class="dt-pre">${dtEscape(v)}</pre></div>`;
      }
      const val = typeof v === 'object' ? JSON.stringify(v) : String(v);
      return `<div class="dt-kv-row"><span class="dt-kv-key">${dtEscape(k)}</span><span class="dt-kv-val">${dtEscape(val)}</span></div>`;
    }).join('');
    return html;
  }
}

/**
 * 工廠方法集合，取代舊版全域單例 window.devPanel。
 * - createForContainer(container): 用於即時串流訊息，回傳一個 instance，之後用 instance.ingest(payload) 持續更新。
 * - mountHistory(container, payload): 用於歷史訊息一次性掛載（不需要動畫、不需要自動收合）。
 */
const DevTrace = {
  registerSection: dtRegisterSection,
  createForContainer(container) {
    return new DevTraceInstance(container);
  },
  mountHistory(container, payload) {
    if (!payload) return;
    const instance = new DevTraceInstance(container);
    instance.mountStatic(payload);
    return instance;
  },
};

window.DevTrace = DevTrace;
