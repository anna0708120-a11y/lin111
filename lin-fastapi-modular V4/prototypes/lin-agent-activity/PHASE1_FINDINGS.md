# Lin Agent Activity UI

## Phase 1 findings

### Hermes Fork already provides the event model

The local Hermes Fork is `/Users/anna2/hermes-agent` at the checked-out `main` revision. Its TUI event handler and turn store already model the lifecycle needed here:

- `message.start`, `message.delta`, `message.complete`
- `thinking.delta`
- `reasoning.delta`, `reasoning.available`
- `tool.start`, `tool.generating`, `tool.progress`, `tool.complete`
- `status.update`
- subagent lifecycle events
- an ordered activity/trail state that can contain multiple tool phases in one turn

Important payload fields already available include `tool_id`, `name`, `context`, `args_text`, `preview`, `summary`, `duration_s`, `error`, and result text. Hermes also has shared activity verb/charm content modules. This means Lin should consume event metadata rather than maintain a large tool-name-to-copy table.

### Lin already has an additive Hermes bridge

Relevant Lin files:

- `app/integrations/hermes_bridge.py`: authenticated runtime client, run lifecycle calls, event streaming, and the current browser-safe `restricted_event()` projection.
- `app/integrations/hermes_routes.py`: additive `/hermes/agent-runs` endpoints and SSE event forwarding as `agent_event`.
- `app/web/frontend.py`: existing single-chat SSE handling, `agent_event` dispatch, and existing `.tool-card` styles. The same file contains the protected workgroup UI, which is intentionally out of scope.
- `app/web/routes.py`: existing chat SSE route and `generate_reply_stream` integration.

The existing projection currently exposes lifecycle metadata only: schema/run/sequence/type/status, entity/tool name, duration, bounded previews, and errors. It does not yet expose the full Hermes-native event payload shape. Formal integration should first extend this projection only as needed for the UI adapter, preserving the existing route and call chain.

### Minimal future formal integration shape

```text
Hermes native events
  -> restricted browser-safe event projection
  -> Lin Activity Adapter (single-chat only)
  -> temporary Activity Layer
  -> compact persistent Agent History record
```

Likely formal files are limited to:

- a new small adapter module under `app/integrations/` or the existing frontend event module;
- the existing `restricted_event()` projection, if additional safe fields are required;
- the single-chat renderer/event handler in `app/web/frontend.py` or its existing chat view module;
- a focused test for event ordering, repeated tools, completion, and separation of temporary/history state.

Do not modify the workgroup implementation, Hermes core, or the existing agent execution path.

## Prototype

`prototypes/lin-agent-activity/index.html` is an independent browser-openable prototype. The first version used a generic phone/chat shell; that was corrected after checking the real Lin single-chat implementation.

The current prototype is based on the actual single-chat structure in `app/web/frontend.py` and `static/js/chat_view.js`:

- `#pg-chat`
- `.chat-topbar`
- `#cm.cms`
- `.clabel`, `.tdiv`
- `.msg`, `.msg-row`, `.msg-avatar`, `.bub`, `.mtime2`
- `.ciw`, `.ci`, `.sb`
- the existing bottom `.tab-bar`

The prototype deliberately does not use the Workgroup DOM (`.workgroup-*`) or the previous generic `.phone`, `.message`, `.stream`, and `.composer` shell.

The simulated flow covers:

1. ordinary user and Lin messages;
2. Hermes-like `thinking.delta`;
3. first `tool.start`, `tool.progress`, and `tool.complete`;
4. Lin re-checking after an uncertain result;
5. second `tool.start`, `tool.progress`, and `tool.complete`;
6. temporary live Activity removal;
7. normal Lin continuation;
8. persistent History generated from the recorded event array;
9. clickable History expansion showing both Tool calls and their event details;
10. clickable individual History rows for detail expansion.

The event array is the source for the History snapshot. The final Lin text is not used to infer or reconstruct the Tool history. Both Tool IDs (`search-1`, `search-2`) remain separate in the completed History.

## Verification

- HTML parser: passed.
- Inline JavaScript syntax check with Node: passed.
- Prototype contains no Workgroup markup or generic previous-shell classes: passed.
- Formal `app/` and `static/js/` tree diff: empty.
- Browser automation: blocked because no Chrome instance is running in the current desktop environment; no visual result is claimed here.

Open the prototype directly:

```text
lin-fastapi-modular V4/prototypes/lin-agent-activity/index.html
```
