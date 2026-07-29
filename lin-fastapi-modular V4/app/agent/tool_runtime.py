"""
Tool Runtime —— Agent Layer 的工具執行骨架。

定位：這是「任何 Tool 怎麼跑、怎麼跟 Timeline 對話」的通用介面，
本身不包含任何具體 Tool 的實作（沒有 Browser、沒有 Vision、沒有 Planner）。
這次只交付骨架本身 + 一個最小可行的參考實作（EchoTool，純用來驗證流程），
Memory Pipeline 仍走既有的 TraceCollector Facade，不改動、不強行套用這層。

為什麼需要這一層（而不是每個 Tool 自己呼叫 timeline.emit）：
    - 每個 Tool 要嘛忘記 emit "running"，要嘛忘記在例外發生時 emit "failed"，
      這類疏漏會讓 Timeline 卡在 running 狀態、永遠不會收尾。
    - Tool 本身不應該知道 EventBus 的內部欄位（id/type/status/summary/payload），
      只需要知道「我開始了」「我進度到哪」「我結束了/我失敗了」。

設計：
    ToolContext          —— 執行期間傳給 Tool 的「進度回報」handle，
                             Tool 呼叫 ctx.progress(summary) 更新同一個 running 事件的
                             summary_history（跑馬燈用），不需要碰 Timeline。
    run_tool(...)         —— 執行一個 Tool 呼叫：
                             1. emit running（呼叫端在這裡就能拿到 SSE，立刻 yield 給前端）
                             2. 執行 Tool 本體（同步函式，接收 ToolContext）
                             3. 依結果 emit success / failed，自動補上 reason
                             全程用 try/except 包住，任何未預期例外都會被轉成
                             failed 事件，不會讓 Timeline 卡在 running。

    Tool 本體的簽名約定（不用繼承任何基底類別，純函式即可）：
        def my_tool(ctx: ToolContext, **kwargs) -> ToolResult
    只要求回傳 ToolResult（或拋例外），其餘實作細節（是否呼叫外部 API、
    是否用 Playwright）完全由 Tool 自己決定，Tool Runtime 不管。

用法（brain.py 或未來任何呼叫端）：
    from app.agent.tool_runtime import run_tool, ToolResult

    def open_browser(ctx, url):
        ctx.progress("Opening Chrome...")
        # ... 實際開瀏覽器 ...
        ctx.progress("Page loaded")
        return ToolResult(summary="Chrome opened", payload={"url": url})

    for sse in run_tool(timeline, id="browser", type="browser",
                         fn=open_browser, kwargs={"url": "https://x.com"}):
        yield sse   # 每次 emit（running / progress / success|failed）都會即時吐一次 SSE

這次範圍邊界：
    - 不實作任何真實 Tool（Browser/Vision/OCR/Planner 都不在這次交付內）。
    - 不改動 Memory Pipeline 的執行順序或業務邏輯，TraceCollector 保持原樣。
    - 不做非同步/併發執行（多個 Tool 同時跑、Tool 內部起 thread）——
      這次只解決「單個 Tool 同步執行 + 事件通知」的骨架，併發排程留給下一輪。
"""
import time


class ToolResult:
    """
    Tool 執行成功時的回傳值。

    summary: 給人看的一句話收尾訊息（例如 "Chrome opened"），會成為 success 事件的 summary。
    payload: 結構化細節，Renderer 目前不強制使用，保留給未來 Analytics/其他消費者。
    """

    def __init__(self, summary=None, payload=None):
        self.summary = summary
        self.payload = payload or {}


class ToolError(Exception):
    """
    Tool 主動判定「這次執行失敗」時可以拋出這個例外（而不是讓未預期的例外往外飛）。
    reason 會直接成為 failed 事件的 reason，summary 可選，沒給就用 reason 頂替。
    """

    def __init__(self, reason, summary=None):
        super().__init__(reason)
        self.reason = reason
        self.summary = summary


class ToolContext:
    """
    執行期間傳給 Tool 本體的「進度回報」handle。
    Tool 只知道呼叫 ctx.progress(summary)，不需要知道 Timeline/EventBus 存在。

    因為 Tool 本體是同步函式、run_tool 是一般函式而非 generator 驅動 Tool 本體，
    ToolContext 把每次 progress() 產生的 SSE 字串先暫存在 _pending，
    由 run_tool 執行完 Tool 本體後统一取出並依序 yield，確保時序仍是
    「running → progress×N → success/failed」，不會被打亂。
    """

    def __init__(self, timeline, id, type):
        self._timeline = timeline
        self._id = id
        self._type = type
        self._pending = []

    def progress(self, summary, payload=None):
        """
        Tool 執行中回報一句話進度，狀態維持 running，summary 疊進 summary_history
        供前端跑馬燈切換顯示。可以在同一次執行內呼叫多次。
        """
        event = self._timeline.emit(self._id, self._type, "running", summary=summary, payload=payload)
        self._pending.append(self._timeline.to_sse(event))

    def drain(self):
        """取出目前累積的 progress SSE 字串，並清空緩衝區。"""
        pending, self._pending = self._pending, []
        return pending


def run_tool(timeline, id, type, fn, kwargs=None, running_summary=None):
    """
    執行一個 Tool 呼叫，全程對應 Timeline 事件，逐一 yield SSE 字串。

    timeline:        Timeline 實例（Event Bus），呼叫端已建立好的那一個。
    id:              這個 Tool 呼叫對應的事件節點 id（例如 "browser"）。
    type:            事件 type，供前端 Renderer 分類（例如 "browser" / "vision"）。
    fn:              Tool 本體，簽名為 fn(ctx: ToolContext, **kwargs) -> ToolResult，
                     也可以直接拋例外（或拋 ToolError）表示失敗。
    kwargs:          傳給 fn 的參數 dict。
    running_summary: 一開始 emit "running" 事件時的預設 summary
                     （例如 "Opening Chrome..."），可省略。

    這是一般函式（generator），用法：
        for sse in run_tool(timeline, id="browser", type="browser", fn=open_browser,
                             kwargs={"url": "https://x.com"}):
            yield sse
    """
    ctx = ToolContext(timeline, id, type)

    start_event = timeline.emit(id, type, "running", summary=running_summary)
    yield timeline.to_sse(start_event)

    try:
        result = fn(ctx, **(kwargs or {}))
        for sse in ctx.drain():
            yield sse

        summary = result.summary if isinstance(result, ToolResult) else None
        payload = result.payload if isinstance(result, ToolResult) else None
        done_event = timeline.emit(id, type, "success", summary=summary, payload=payload)
        yield timeline.to_sse(done_event)

    except ToolError as e:
        for sse in ctx.drain():
            yield sse
        fail_event = timeline.emit(id, type, "failed", summary=e.summary or e.reason, reason=e.reason)
        yield timeline.to_sse(fail_event)

    except Exception as e:
        # 任何未預期例外都要收尾成 failed，不能讓 Timeline 卡在 running。
        for sse in ctx.drain():
            yield sse
        fail_event = timeline.emit(id, type, "failed", summary="執行失敗", reason=str(e))
        yield timeline.to_sse(fail_event)
