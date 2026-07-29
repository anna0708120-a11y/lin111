"""
Trace Collector —— 通用的執行鏈路收集元件。

設計定位：這是一個獨立的基礎元件，不依賴、也不知道 Developer Panel 的存在。
generate_reply_stream() 呼叫它記錄各節點的執行狀態，它只負責收集與組裝，
輸出格式（export）本身可以有多個消費者，Developer Panel 只是其中之一：

    generate_reply_stream
        │
        ▼
    TraceCollector（收集、組裝）
        │
        ├── export() → Developer Panel（本輪接入）
        └── （未來）memory_trace.py 可以改成基於這個收集，不在這一輪處理

欄位命名刻意跟現有 app/memory_trace.py 的既有詞彙對齊（skip_reason / action_taken /
parsed_decision / db 相關欄位），降低以後合併或遷移的成本，但這次不動 memory_trace.py，
也不改動任何非串流路徑。

brain.py 的用法只會是：
    collector = TraceCollector()
    collector.record_prompt(...)
    collector.record_reasoning(...)
    collector.record_memory_decision(...)
    collector.record_parser(...)
    collector.record_backend(...)
    collector.record_db(...)
    yield collector.export_sse()

不需要自己組裝一個大 dict。
"""
import json
import time

SCHEMA_VERSION = 1

# 開放狀態集合；未知狀態一律 fallback 成 "unknown"，不拋錯（沿用 chat_view.js Tool UI 的風格）。
VALID_STATUSES = {"passed", "waiting", "failed", "skipped", "not_executed", "unknown"}

# Skip Reason 詞彙沿用 app/memory_trace.py 既有的定義，方便未來兩邊互通、合併。
SKIP_REASONS = {
    "worth_no": "模型判斷不值得記",
    "parse_failed": "解析 [MEMORY_DECISION] 失敗",
    "already_exists": "keyword 已存在且內容相似（reinforce）",
    "conflict_detected": "衝突待審核",
    "permission_denied": "試圖修改 user 建立的記憶",
    "db_error": "資料庫操作失敗",
}


class TraceCollector:
    """
    收集這一輪對話從 Prompt 組裝到 DB 寫入，各節點（section）的執行狀態。

    Section 採 registry 設計：不是寫死 memory/mood/tool 這幾個名字，
    而是呼叫端要記錄什麼 section 就呼叫 record(section_name, ...)，
    _sections 這個 dict 本身就是 registry，之後新增 Mood/Tool/API/Vision
    等 section，不需要改這個類別的任何程式碼，也不需要改 Developer Panel 主框架
    （前端對應會用同樣的 registerSection 機制處理，見 dev_panel.js）。
    """

    def __init__(self, trace_id=None):
        self.trace_id = trace_id or f"trace_{int(time.time() * 1000)}"
        self._sections = {}
        self._start_time = time.time()

    # ------------------------------------------------------------------
    # 通用底層方法：任何 section 都可以透過這個方法記錄，
    # 下面 record_xxx() 是針對目前 Memory Pipeline 常用節點包的語意化捷徑，
    # 不是必須的固定清單——未來 Mood/Tool/API 可以直接呼叫 record()，
    # 不需要在這個檔案裡新增對應的 record_xxx 方法。
    # ------------------------------------------------------------------
    def record(self, section, status, data=None, reason=None):
        """
        記錄一個 section 的執行結果。

        section: 字串，例如 "prompt" / "reasoning" / "memory_decision" / "parser" /
                 "permission_check" / "conflict" / "database" / "memory_summary"，
                 或未來的 "mood" / "tool" / "api" / "vision" 等，不限定固定清單。
        status:  "passed" / "waiting" / "failed" / "skipped" / "not_executed"。
        data:    dict，這個 section 展開後要顯示的細節。
        reason:  字串，簡短說明這個狀態的原因（沿用 SKIP_REASONS 詞彙時盡量對齊 key）。
        """
        norm_status = status if status in VALID_STATUSES else "unknown"
        self._sections[section] = {
            "status": norm_status,
            "reason": reason,
            "data": data or {},
            "ts": time.time(),
        }

    # ------------------------------------------------------------------
    # 語意化捷徑：對應 Memory Pipeline 的常見節點，內部仍然只是呼叫 record()。
    # 欄位命名跟 app/memory_trace.py 保持一致，方便未來遷移合併。
    # ------------------------------------------------------------------
    def record_prompt(self, status, prompt_version=None, total_tokens=None, memory_rule_loaded=None, mood_rule_loaded=None):
        self.record("prompt", status, data={
            "prompt_version": prompt_version,
            "total_tokens": total_tokens,
            "memory_rule_loaded": memory_rule_loaded,
            "mood_rule_loaded": mood_rule_loaded,
        })

    def record_reasoning(self, status, reasoning_text=None):
        self.record("reasoning", status, data={
            "reasoning_text": reasoning_text,
            "length": len(reasoning_text) if reasoning_text else 0,
        })

    def record_memory_decision(self, status, parsed_decision=None, reason=None):
        """對應 memory_trace.py 的 record_parse_result 概念，欄位名用 parsed_decision 對齊。"""
        self.record("memory_decision", status, data={"parsed_decision": parsed_decision}, reason=reason)

    def record_parser(self, status, reason=None, parse_time_ms=None):
        self.record("parser", status, data={"parse_time_ms": parse_time_ms}, reason=reason)

    def record_backend(self, status, backend_action=None, action_taken=None, reason=None):
        """對應 memory_trace.py 的 record_backend_action 概念。"""
        self.record("backend", status, data={
            "backend_action": backend_action,
            "action_taken": action_taken,
        }, reason=reason)

    def record_db(self, status, memory_id=None, db_error=None):
        """對應 memory_trace.py 的 record_db_result 概念，欄位名用 db_error 對齊。"""
        self.record("database", status, data={
            "memory_id": memory_id,
            "db_error": db_error,
        }, reason=db_error)

    def elapsed_ms(self):
        return int((time.time() - self._start_time) * 1000)

    # ------------------------------------------------------------------
    # 輸出層：export() 是給任何消費者用的通用介面，Developer Panel 只是其中之一。
    # ------------------------------------------------------------------
    def export(self):
        """組成版本化 payload，供任何消費者使用（Developer Panel / 未來的 memory_trace 等）。"""
        return {
            "version": SCHEMA_VERSION,
            "trace_id": self.trace_id,
            "duration_ms": self.elapsed_ms(),
            "sections": self._sections,
        }

    def export_sse(self):
        """組成可以直接 yield 給前端的 SSE 事件字串（Developer Panel 用的是這個）。"""
        payload = self.export()
        return f"event: devtrace\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
