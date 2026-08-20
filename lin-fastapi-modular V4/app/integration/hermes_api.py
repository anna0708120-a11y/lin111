"""Minimal Lin -> Hermes Agent API client.

Hermes owns the agent loop and tool execution. Lin only submits a bounded run
and polls its terminal status; no provider or tool credentials cross this
boundary.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HermesAPIError(RuntimeError):
    """A controlled Hermes API failure."""


@dataclass(frozen=True)
class HermesConfig:
    base_url: str
    api_key: str
    timeout_seconds: float = 30.0
    poll_interval_seconds: float = 1.0
    max_wait_seconds: float = 300.0


def load_config() -> HermesConfig:
    base_url = (
        os.getenv("HERMES_AGENT_URL")
        or os.getenv("HERMES_URL")
        or os.getenv("HERMES_API_BASE_URL")
        or ""
    ).rstrip("/")
    api_key = os.getenv("HERMES_API_KEY") or os.getenv("API_SERVER_KEY") or ""
    if not base_url or not api_key:
        raise HermesAPIError("Hermes API is not configured")
    return HermesConfig(
        base_url=base_url.removesuffix("/v1"),
        api_key=api_key,
        timeout_seconds=float(os.getenv("HERMES_API_TIMEOUT_SECONDS", "30")),
        poll_interval_seconds=float(os.getenv("HERMES_API_POLL_INTERVAL_SECONDS", "1")),
        max_wait_seconds=float(os.getenv("HERMES_API_MAX_WAIT_SECONDS", "300")),
    )


def _request(config: HermesConfig, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(
        f"{config.base_url}{path}",
        data=payload,
        method=method,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {config.api_key}",
            **({"Content-Type": "application/json"} if payload is not None else {}),
        },
    )
    try:
        with urlopen(request, timeout=config.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raise HermesAPIError(f"Hermes API returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise HermesAPIError("Hermes API is unreachable") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HermesAPIError("Hermes API returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise HermesAPIError("Hermes API returned an invalid object")
    return value


def list_models(config: HermesConfig | None = None) -> dict[str, Any]:
    return _request(config or load_config(), "GET", "/v1/models")


def run_task(prompt: str, *, config: HermesConfig | None = None, model: str | None = None) -> dict[str, Any]:
    if not prompt or not prompt.strip():
        raise HermesAPIError("Task prompt must not be empty")
    cfg = config or load_config()
    body: dict[str, Any] = {"input": prompt.strip()}
    if model:
        body["model"] = model
    started = _request(cfg, "POST", "/v1/runs", body)
    run_id = started.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise HermesAPIError("Hermes API did not return a run_id")
    deadline = time.monotonic() + cfg.max_wait_seconds
    while time.monotonic() < deadline:
        status = _request(cfg, "GET", f"/v1/runs/{run_id}")
        state = status.get("status")
        if state == "completed":
            return {"run_id": run_id, "status": state, "result": status.get("output", ""), "raw": status}
        if state in {"failed", "cancelled", "expired"}:
            raise HermesAPIError(f"Hermes run {state}: {status.get('error', 'unknown error')}")
        time.sleep(cfg.poll_interval_seconds)
    raise HermesAPIError("Hermes task timed out")
