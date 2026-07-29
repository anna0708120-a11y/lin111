/**
 * Developer Tool Panel
 *
 * 開發模式專用面板，用來 3 秒知道現在卡在哪一層，避免一直翻 Render Logs。
 * 消費後端 TraceCollector（app/agent/trace_collector.py）輸出的 `event: devtrace`。
 *
 * 可擴展設計：
 *   - 後端 sections 是任意 key 的 dict（不寫死 memory/mood/tool），
 *     前端收到任何 section 都會自動渲染，不需要事先註冊已知清單。
 *   - SECTION_META 只是「已知 section 的展示優化」（icon、順序、展開時的自訂 renderer），
 *     沒有寫進 SECTION_META 的 section 一樣會顯示，只是用預設樣式 fallback，
 *     不會被吃掉或報錯（跟 chat_view.js 的 Tool UI 卡片同一個設計原則）。
 *   - 之後 Mood / Tool Calling / API / Vision 等模組要加自己的 Section，
 *     只需要：
 *       1. 後端呼叫 collector.record("mood", status, data, reason) 之類的方法
 *       2. （可選）前端呼叫 DevPanel.registerSection("mood", { icon, order, renderDetail })
 *          來自訂展開時的細節渲染，不註冊也能顯示，只是用預設格式
 *     不需要改這個檔案的核心渲染流程。
 *
 * 版本相容：devtrace payload 帶 version 欄位，目前只認 version 1，
 * 遇到不認得的 version 一律 fallback 成「盡量顯示看得懂的欄位」，不拋錯、不整個面板消失。
 */

const STATUS_ICON = {
  passed: '🟢',
  waiting: '🟡',
  failed: '🔴',
  skipped: '⚪',
  not_executed: '⚪',
  unknown: '⚪',
};

const STATUS_LABEL = {
  passed: 'Passed',
  waiting: 'Waiting',
  failed: 'Failed',
  skipped: 'Skipped',
  not_executed: 'Not Executed',
  unknown: 'Unknown',
};

// Pipeline 顯示順序（沒列在這裡的 section 會照後端傳來的順序接在後面，不會消失）。
const PIPELINE_ORDER = ['prompt', 'reasoning', 'memory_decision', 'parser', 'backend', 'database'];

// 已知 section 的展示優化（display name / icon），未知 section 用 key 本身當標題。
const SECTION_META = {
  prompt: { title: 'Prompt' },
  reasoning: { title: 'Reasoning' },
  memory_decision: { title: 'MEMORY_DECISION' },
  parser: { title: 'Parser' },
  backend: { title: 'Backend' },
  database: { title: 'Database' },
  mood: { title: 'Mood' },
  tool: { title: 'Tool Calling' },
  api: { title: 'API' },
  trace: { title: 'Trace' },
};

class DevPanel {
  constructor() {
    this.rootEl = null;
    this.summaryEl = null;
    this.bodyEl = null;
    this.expanded = false;
    this.sectionState = {}; // sectionKey -> { expanded: bool }
    this.customRenderers = {}; // sectionKey -> function(data) -> html string
    this.lastPayload = null;
  }

  init() {
    if (document.getElementById('devPanelRoot')) return; // 避免重複插入

    const root = document.createElement('div');
    root.id = 'devPanelRoot';
    root.className = 'dev-panel collapsed';
    root.innerHTML = `
      <div class="dev-panel-summary" id="devPanelSummary">
        <span class="dev-panel-dot">⚪</span>
        <span class="dev-panel-summary-text">Developer Tool</span>
      </div>
      <div class="dev-panel-body" id="devPanelBody" style="display:none;"></div>
    `;
    document.body.appendChild(root);

    this.rootEl = root;
    this.summaryEl = root.querySelector('#devPanelSummary');
    this.bodyEl = root.querySelector('#devPanelBody');

    this.summaryEl.addEventListener('click', () => this.toggle());
  }

  toggle() {
    this.expanded = !this.expanded;
    this.bodyEl.style.display = this.expanded ? 'block' : 'none';
    this.rootEl.classList.toggle('collapsed', !this.expanded);
    this.rootEl.classList.toggle('expanded', this.expanded);
  }

  /**
   * 給其他模組（Mood/Tool/API...）自訂某個 section 展開後的細節渲染方式。
   * 不呼叫這個也完全沒問題，未註冊的 section 會用預設的 key: value 列表渲染。
   */
  registerSection(key, { title, renderDetail } = {}) {
    if (title) {
      SECTION_META[key] = Object.assign({}, SECTION_META[key], { title });
    }
    if (typeof renderDetail === 'function') {
      this.customRenderers[key] = renderDetail;
    }
  }

  /**
   * 接收一筆 devtrace payload（來自 SSE `event: devtrace`）。
   * payload 結構：{ version, trace_id, duration_ms, sections: { [key]: {status, reason, data, ts} } }
   */
  ingest(payload) {
    if (!payload || typeof payload !== 'object') return;
    this.lastPayload = payload;

    if (payload.version !== 1) {
      // 未知版本：不拋錯，盡量以現有欄位繼續顯示，只是不做版本專屬的特殊處理。
      console.warn('[DevPanel] 收到未知 devtrace version:', payload.version);
    }

    this._renderSummary(payload);
    this._renderBody(payload);
  }

  _overallStatus(sections) {
    const values = Object.values(sections || {});
    if (values.some(s => s.status === 'failed')) return 'failed';
    if (values.some(s => s.status === 'waiting')) return 'waiting';
    if (values.length > 0 && values.every(s => s.status === 'passed' || s.status === 'skipped')) return 'passed';
    return 'unknown';
  }

  _renderSummary(payload) {
    const sections = payload.sections || {};
    const overall = this._overallStatus(sections);
    const icon = STATUS_ICON[overall] || '⚪';

    // 找出第一個 failed 的 section，摘要文字優先顯示它卡在哪裡，符合「3 秒知道卡在哪一層」的目標。
    const failedEntry = Object.entries(sections).find(([, v]) => v.status === 'failed');
    let text;
    if (failedEntry) {
      const [key, val] = failedEntry;
      const title = (SECTION_META[key] && SECTION_META[key].title) || key;
      text = `${title} Failed${val.reason ? '：' + val.reason : ''}`;
    } else if (overall === 'passed') {
      text = 'Memory Ready';
    } else if (overall === 'waiting') {
      text = 'Waiting...';
    } else {
      text = 'Developer Tool';
    }

    const dotEl = this.summaryEl.querySelector('.dev-panel-dot');
    const textEl = this.summaryEl.querySelector('.dev-panel-summary-text');
    if (dotEl) dotEl.textContent = icon;
    if (textEl) textEl.textContent = text;
  }

  _renderBody(payload) {
    const sections = payload.sections || {};
    const keys = Object.keys(sections);
    // 已知 pipeline 順序優先，其餘未知 section 接在後面，不會消失。
    const ordered = [
      ...PIPELINE_ORDER.filter(k => keys.includes(k)),
      ...keys.filter(k => !PIPELINE_ORDER.includes(k)),
    ];

    let html = `<div class="dev-panel-meta">trace_id: ${_dpEscape(payload.trace_id || '')} · ${payload.duration_ms != null ? payload.duration_ms + 'ms' : ''}</div>`;

    ordered.forEach(key => {
      const section = sections[key];
      const meta = SECTION_META[key] || {};
      const title = meta.title || key;
      const icon = STATUS_ICON[section.status] || '⚪';
      const label = STATUS_LABEL[section.status] || section.status;
      const isOpen = !!(this.sectionState[key] && this.sectionState[key].expanded);

      const detailHtml = isOpen ? this._renderSectionDetail(key, section) : '';

      html += `
        <div class="dev-panel-section" data-section="${_dpEscape(key)}">
          <div class="dev-panel-section-head" onclick="window.devPanel._toggleSection('${_dpEscape(key)}')">
            <span class="dev-panel-arrow">${isOpen ? '▼' : '▶️'}</span>
            <span class="dev-panel-section-icon">${icon}</span>
            <span class="dev-panel-section-title">${_dpEscape(title)}</span>
            <span class="dev-panel-section-status">${_dpEscape(label)}</span>
          </div>
          <div class="dev-panel-section-detail">${detailHtml}</div>
        </div>`;
    });

    this.bodyEl.innerHTML = html;
  }

  _toggleSection(key) {
    if (!this.sectionState[key]) this.sectionState[key] = { expanded: false };
    this.sectionState[key].expanded = !this.sectionState[key].expanded;
    if (this.lastPayload) this._renderBody(this.lastPayload);
  }

  _renderSectionDetail(key, section) {
    if (this.customRenderers[key]) {
      try {
        return this.customRenderers[key](section);
      } catch (e) {
        console.error('[DevPanel] custom renderer error for section', key, e);
      }
    }

    // 預設渲染：reason（如果有）+ data 裡的 key: value 逐行列出。
    let html = '';
    if (section.reason) {
      html += `<div class="dev-panel-reason">Reason: ${_dpEscape(section.reason)}</div>`;
    }
    const data = section.data || {};
    const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined && v !== '');
    if (entries.length === 0 && !section.reason) {
      html += `<div class="dev-panel-empty">No data.</div>`;
      return html;
    }
    if (entries.length > 0) {
      html += '<div class="dev-panel-kv">' + entries.map(([k, v]) => {
        let displayVal = v;
        if (typeof v === 'object') displayVal = JSON.stringify(v);
        // reasoning_text 特別長，用可滾動、可複製的區塊呈現，而不是塞進單行 kv。
        if (k === 'reasoning_text' && typeof v === 'string' && v.length > 0) {
          return `<div class="dev-panel-reasoning-block"><div class="dev-panel-kv-key">${_dpEscape(k)}</div><pre class="dev-panel-reasoning-pre">${_dpEscape(v)}</pre></div>`;
        }
        return `<div class="dev-panel-kv-row"><span class="dev-panel-kv-key">${_dpEscape(k)}</span><span class="dev-panel-kv-val">${_dpEscape(String(displayVal))}</span></div>`;
      }).join('') + '</div>';
    }
    return html;
  }
}

function _dpEscape(str) {
  const div = document.createElement('div');
  div.textContent = str == null ? '' : String(str);
  return div.innerHTML;
}

// 全域單例，跟 chat_view.js 的 window.chatView 是同一種掛法。
window.devPanel = window.devPanel || new DevPanel();
