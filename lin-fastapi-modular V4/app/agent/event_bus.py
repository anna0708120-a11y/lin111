"""
Event Bus —— Agent 的唯一 Event Source。

定位：這不是 Developer Panel 的專屬元件，是整個 Agent 未來所有能力
（Memory / Browser / Vision / Planner / Tool Calling）共用的事件層。

Timeline 只負責三件事：
    1. 保存目前每個事件節點的最新狀態（Map<id, event>）
    2. emit() 一個事件：更新該 id 的記錄，回傳這次事件本身（給呼叫端決定要不要 yield/SSE）
    3. export_all()：回傳目前所有事件節點的快照（給歷史 replay / 完整重建用）

Timeline 不認識 Memory、Browser、Vision 是什麼，也不包含任何業務邏輯。
它只認識六個欄位：id / type / status / summary / payload / reason（+ updated_at 自動打上）。
「type 是什麼」「status 該怎麼畫」「summary 怎麼顯示」全部交給前端 Renderer 依 type 決定，
Timeline 本身不 hardcode 任何具體領域的判斷。

summary 是給人看的一句話（例如 "Opening Chrome..." / "Checking memories..."），
Timeline 本身不組字串、不翻譯業務資料，一律由呼叫端（Tool/Facade）直接給定。
同一個 id 連續 emit 且每次 summary 不同時，Timeline 會自動把 summary 疊進
summary_history（例如 Browser 從 "Opening Chrome..." 到 "Taking screenshot..."
到 "Clicking..." 這種同一個 running 狀態下換好幾句話的情況），前端可以拿
summary_history 做跑馬燈式切換動畫，不需要自己維護歷史。

用法（由語意化 Facade，例如 trace_collector.py，呼叫，不建議業務程式碼直接裸呼叫）：
    timeline = Timeline()
    event = timeline.emit(id="prompt", type="memory", status="success", summary="Prompt ready")
    yield timeline.to_sse(event)
    ...
    snapshot = timeline.export_all()   # {"prompt": {...}, "memory": {...}, ...}
"""
import json
import time

VALID_STATUSES = {"running", "success", "failed", "skipped", "not_executed", "unknown"}

# 同一個 id 的 summary_history 最多保留幾則，避免長時間 running 的 Tool
# （例如反覆截圖的 Browser）把單一事件的 payload 撐爆。
MAX_SUMMARY_HISTORY = 20

SCHEMA_VERSION = 2


class Timeline:
    """
    唯一 Event Source。內部是一個以 id 為 key 的 Map，emit 同一個 id 會覆蓋更新
    （而不是 append），這樣像 Browser 這種可能連續 running→running→success 的
    事件，Timeline 不會無限增長，前端也只需要更新同一個 node。
    """

    def __init__(self, trace_id=None):
        self.trace_id = trace_id or f"trace_{int(time.time() * 1000)}"
        self._events = {}  # id -> event dict
        self._start_time = time.time()

    def emit(self, id, type, status, summary=None, payload=None, reason=None):
        """
        發出（或更新）一個事件節點。

        id:      事件節點的穩定鍵，同一個 id 再次 emit 會覆蓋，不會 append。
                 例如 "prompt" / "memory" / "browser" / 未來任何領域自訂的 id。
        type:    給 Renderer 分類用的字串，Timeline 不解析、不限定清單。
        status:  "running" / "success" / "failed" / "skipped" / "not_executed"，
                 不在 VALID_STATUSES 裡的值 fallback 成 "unknown"，不拋錯。
        summary: 給人看的一句話，例如 "Opening Chrome..."。這是 UI 主要顯示的內容，
                 Timeline 不組字串，呼叫端要給就是完整的一句話。
        payload: dict，這個事件附帶的細節（給未來需要結構化資料的消費者用，
                 例如 Analytics），Renderer 目前只顯示 summary，不強制要求 payload。
        reason:  可選，簡短說明 failed/skipped 的原因。

        回傳：這次 emit 之後的單一 event dict（不是全體快照），
              呼叫端可以直接拿去 to_sse() 或做其他用途。
        """
        norm_status = status if status in VALID_STATUSES else "unknown"
        prev = self._events.get(id)
        history = list(prev["summary_history"]) if prev else []
        if summary and (not history or history[-1] != summary):
            history.append(summary)
            if len(history) > MAX_SUMMARY_HISTORY:
                history = history[-MAX_SUMMARY_HISTORY:]

        event = {
            "id": id,
            "type": type,
            "status": norm_status,
            "summary": summary,
            "summary_history": history,
            "payload": payload or {},
            "reason": reason,
            "updated_at": time.time(),
        }
        self._events[id] = event
        return event

    def export_all(self):
        """回傳目前所有事件節點的快照，供歷史 replay / 完整重建使用。"""
        return {
            "version": SCHEMA_VERSION,
            "trace_id": self.trace_id,
            "step_count": self.step_count(),
            "duration_ms": self.duration_ms(),
            "events": dict(self._events),
        }

    def step_count(self):
        """目前累積了多少個不同 id 的事件節點（給 Header 顯示 "N steps" 用）。"""
        return len(self._events)

    def duration_ms(self):
        """
        Header 顯示用的耗時：最後一個事件的 updated_at 減去第一個事件的 updated_at。
        沒有事件時回傳 0，只有一個事件時回傳 0（還沒有跨度可言）。
        刻意不用 time.time() - _start_time，因為那包含了「還沒發生第一個事件前」
        的等待時間，不是使用者關心的「Agent 實際工作了多久」。
        """
        if not self._events:
            return 0
        timestamps = [e["updated_at"] for e in self._events.values()]
        return int((max(timestamps) - min(timestamps)) * 1000)

    def elapsed_ms(self):
        """舊名保留相容：等同 duration_ms()，之後統一改呼叫 duration_ms()。"""
        return self.duration_ms()

    def to_sse(self, event):
        """
        把單一事件組成可以直接 yield 給前端的 SSE 字串。
        事件名固定用 agent_event，取代舊版一次性的 devtrace。
        """
        payload = {
            "version": SCHEMA_VERSION,
            "trace_id": self.trace_id,
            "event": event,
        }
        return f"event: agent_event\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
