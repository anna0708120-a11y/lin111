# Lin Hermes Integration

Lin remains the only user-facing application. Hermes runs as an independent Render service and supplies Agent execution, tools, skills, toolsets, MCP, delegation, sessions, and model/provider runtime.

## Included Surfaces

- Lin API bridge: `app/integrations/hermes_bridge.py`
- Lin run proxy and browser-safe SSE projection: `app/integrations/hermes_routes.py`
- Lin-only Hermes Settings proxy: `app/integrations/hermes_management_proxy.py`
- Settings entry: `/agent-settings`
- Dwell-style Spaces entry: `/spaces`
- Existing group chat entry: the `群聊` card navigates to `/?view=workgroup`

The group-chat implementation is not replaced or modified by this integration.

## Runtime Contract

Lin calls the isolated Hermes Runtime using:

- `POST /agent-runs`
- `GET /agent-runs/{run_id}`
- `GET /agent-runs/{run_id}/events`
- `POST /agent-runs/{run_id}/cancel`

The event projection is intentionally limited to lifecycle metadata: `run_id`, sequence, event type/status, entity/tool name, duration, and bounded previews/errors. Full tool output is not forwarded to a browser.

## Render Configuration

Configure these secrets on the Lin service:

- `HERMES_RUNTIME_URL`
- `HERMES_RUNTIME_TOKEN`
- `HERMES_MANAGEMENT_URL`
- `HERMES_MANAGEMENT_TOKEN`

Configure the matching service tokens on the Hermes Runtime and Hermes Management services. Hermes runs with memory and SOUL identity loading disabled for Lin requests, so Lin remains the authority for persona, Memory, Life, Context, Proactive behavior, and final response decisions.

## Scope Boundary

This integration does not change Lin's protected `app/agent/*` core modules, Memory, Life, Context, Proactive, existing chat behavior, or group-chat implementation.
