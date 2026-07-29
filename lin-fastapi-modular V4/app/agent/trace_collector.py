"""
Trace Collector —— Memory Pipeline 專用的語意化 Facade，包在 Timeline（Event Bus）外面。

定位（重構後）：
    這個檔案不再是「收集完整報告、最後一次 export」的 Report Collector。
    真正的 Event Source 是 app/agent/event_bus.py 的 Timeline，
    這裡只是讓 brain.py 保持可讀性的一層語意化包裝：

        Brain
          │
          ▼
        collector.record_prompt(...)      ← brain.py 只描述「發生了什麼」
          │
          ▼
        timeline.emit(id="prompt", type="memory", status="success", payload={...})
          │
          ▼
        yield timeline.to_sse(event)      ← brain.py 立刻把這個事件送給前端

    brain.py 不需要知道 id/type 這些 Event Bus 的細節，只需要呼叫
    record_prompt() / record_reasoning() / record_memory_decision() /
    record_parser() / record_backend() / record_db()，這幾個方法名維持不變，
    降低這次重構對 brain.py 呼叫端的改動幅度。

    以後如果 payload 格式要調整，只需要改這個檔案裡的 record_xxx()，
    不需要在 brain.py 裡到處搜尋 emit(...) 呼叫。

Timeline 是唯一 Event Source，不是只服務 Developer Panel——
Memory 只是第一個 Consumer，之後 Browser / Vision / Planner / Tool Calling
都可以直接呼叫 timeline.emit(id=..., type=..., ...)，不需要新增專屬的
XxxCollector 類別，也不需要改 Timeline 本體或 dev_panel.js 的渲染邏輯。

這次重構範圍：只讓 Memory Pipeline 跑在 Timeline 架構上，
不加入 Browser / Vision / OCR / Tool Calling / 假等待動畫。
"""
from app.agent.event_bus import Timeline

# type 固定用 "memory"：這次範圍內，prompt/reasoning/memory_decision/parser/
# backend/database 六個節點全部屬於 Memory Pipeline，用同一個 type 方便前端
# Renderer 用同一種畫法呈現這一組節點。未來 Browser/Vision 等會是別的 type，
# 不會跟這裡混在一起。
_MEMORY_TYPE = "memory"

# Skip Reason 詞彙沿用既有 app/memory_trace.py 的定義，方便未來兩邊互通、合併。
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
    Memory Pipeline 的語意化 Facade。內部持有一個 Timeline 實例（Event Bus），
    record_xxx() 方法把「發生了什麼」翻譯成 timeline.emit(id=..., type="memory", ...)，
    每次呼叫都回傳這次事件的 SSE 字串，brain.py 直接 yield 即可。

    summary 由這個檔案負責產生（Timeline 本身不組字串）：Memory Pipeline 的業務
    語意只有這裡最清楚，所以每個 record_xxx() 依 status/reason 決定要顯示的
    一句話，前端 Activity Timeline 直接顯示這句話，不解析 payload。
    """

    # brain.py 沿用舊版狀態詞彙呼叫 record_xxx("passed", ...)，
    # 這裡統一映射成 Timeline 認識的 "success"，不需要改動 brain.py 既有的呼叫字串。
    _STATUS_ALIASES = {"passed": "success"}

    def __init__(self, trace_id=None):
        self.timeline = Timeline(trace_id=trace_id)

    def _norm(self, status):
        return self._STATUS_ALIASES.get(status, status)

    @property
    def trace_id(self):
        return self.timeline.trace_id

    def elapsed_ms(self):
        return self.timeline.elapsed_ms()

    # ------------------------------------------------------------------
    # 語意化方法：brain.py 只呼叫這些，不直接碰 timeline.emit()。
    # 每個方法都回傳「這次事件對應的 SSE 字串」，brain.py 直接 yield 即可，
    # 這樣每個 record 呼叫點天然就是一次即時的事件推送，不用等到最後才打包。
    # ------------------------------------------------------------------
    def record_prompt(self, status, prompt_version=None, total_tokens=None, memory_rule_loaded=None, mood_rule_loaded=None):
        norm = self._norm(status)
        summary = "Preparing prompt..." if norm == "running" else (
            "Prompt ready" if norm == "success" else "Prompt failed"
        )
        event = self.timeline.emit("prompt", _MEMORY_TYPE, norm, summary=summary, payload={
            "prompt_version": prompt_version,
            "total_tokens": total_tokens,
            "memory_rule_loaded": memory_rule_loaded,
            "mood_rule_loaded": mood_rule_loaded,
        })
        return self.timeline.to_sse(event)

    def record_reasoning(self, status, reasoning_text=None):
        norm = self._norm(status)
        summary = "Reasoning received" if norm == "success" else "Reasoning unavailable"
        event = self.timeline.emit("reasoning", _MEMORY_TYPE, norm, summary=summary, payload={
            "reasoning_text": reasoning_text,
            "length": len(reasoning_text) if reasoning_text else 0,
        })
        return self.timeline.to_sse(event)

    def record_memory_decision(self, status, parsed_decision=None, reason=None):
        """對應舊版 memory_trace.py 的 record_parse_result 概念，欄位名用 parsed_decision 對齊。"""
        norm = self._norm(status)
        summary = "Decision parsed" if norm == "success" else (SKIP_REASONS.get(reason, reason) or "Decision parsing failed")
        event = self.timeline.emit("memory_decision", _MEMORY_TYPE, norm, summary=summary,
                                    payload={"parsed_decision": parsed_decision}, reason=reason)
        return self.timeline.to_sse(event)

    def record_parser(self, status, reason=None, parse_time_ms=None):
        norm = self._norm(status)
        summary = "Parser OK" if norm == "success" else (SKIP_REASONS.get(reason, reason) or "Parser failed")
        event = self.timeline.emit("parser", _MEMORY_TYPE, norm, summary=summary,
                                    payload={"parse_time_ms": parse_time_ms}, reason=reason)
        return self.timeline.to_sse(event)

    def record_backend(self, status, backend_action=None, action_taken=None, reason=None):
        """對應舊版 memory_trace.py 的 record_backend_action 概念。"""
        norm = self._norm(status)
        if norm == "not_executed":
            summary = "Nothing to save"
        elif norm == "success":
            summary = "Memory pipeline executed"
        else:
            summary = SKIP_REASONS.get(reason, reason) or "Backend failed"
        event = self.timeline.emit("backend", _MEMORY_TYPE, norm, summary=summary, payload={
            "backend_action": backend_action,
            "action_taken": action_taken,
        }, reason=reason)
        return self.timeline.to_sse(event)

    def record_db(self, status, memory_id=None, db_error=None):
        """對應舊版 memory_trace.py 的 record_db_result 概念，欄位名用 db_error 對齊。"""
        norm = self._norm(status)
        if norm == "success":
            summary = "Memory saved"
        elif norm == "skipped":
            summary = SKIP_REASONS.get(db_error, db_error) or "Memory not saved"
        elif norm == "not_executed":
            summary = "No memory action"
        else:
            summary = db_error or "Database failed"
        event = self.timeline.emit("database", _MEMORY_TYPE, norm, summary=summary, payload={
            "memory_id": memory_id,
            "db_error": db_error,
        }, reason=db_error)
        return self.timeline.to_sse(event)

    # ------------------------------------------------------------------
    # 輸出層：export() 回傳目前 Timeline 的完整快照，供歷史 replay 使用
    # （state.add_conversation_turn(..., trace=collector.export()) 走這條）。
    # ------------------------------------------------------------------
    def export(self):
        return self.timeline.export_all()
