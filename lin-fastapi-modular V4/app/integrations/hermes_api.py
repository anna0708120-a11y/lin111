"""Minimal client for Hermes Agent's official Responses API.

This client deliberately uses the public API-server contract rather than the
legacy Lin-specific ``/agent-runs`` runtime protocol. Hermes owns execution of
its configured tools, skills, and MCP servers; Lin receives only the completed
response plus a small tool-call summary for verification.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests


class HermesAPIError(RuntimeError):
    """Controlled error at the Lin-to-Hermes official API boundary."""


@dataclass(frozen=True)
class HermesAPIConfig:
    base_url: str
    api_key: str
    model: str
    connect_timeout: float = 5.0
    read_timeout: float = 120.0

    @classmethod
    def from_env(cls) -> "HermesAPIConfig":
        return cls(
            base_url=(os.getenv("HERMES_API_URL") or os.getenv("HERMES_AGENT_URL") or "").strip(),
            api_key=(os.getenv("HERMES_API_KEY") or os.getenv("HERMES_AGENT_API_KEY") or os.getenv("API_SERVER_KEY") or "").strip(),
            model=(os.getenv("HERMES_MODEL") or os.getenv("HERMES_AGENT_MODEL") or "").strip(),
            connect_timeout=float(os.getenv("HERMES_API_CONNECT_TIMEOUT", "5")),
            read_timeout=float(os.getenv("HERMES_API_READ_TIMEOUT", "120")),
        )

    def normalized_base_url(self) -> str:
        """Return the API origin, accepting either origin or origin/v1."""
        raw = self.base_url.strip().rstrip("/")
        if not raw:
            return ""
        try:
            parsed = urlsplit(raw)
        except ValueError as exc:
            raise HermesAPIError("HERMES_API_URL is invalid") from exc
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HermesAPIError("HERMES_API_URL must be an absolute http(s) URL")
        if parsed.query or parsed.fragment:
            raise HermesAPIError("HERMES_API_URL must not contain a query or fragment")
        path = parsed.path.rstrip("/")
        if path == "/v1":
            path = ""
        elif path.endswith("/v1"):
            path = path[:-3].rstrip("/")
        return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))

    def validate(self) -> None:
        missing = [
            name
            for name, value in (
                ("HERMES_API_URL", self.base_url),
                ("HERMES_API_KEY", self.api_key),
                ("HERMES_MODEL", self.model),
            )
            if not value
        ]
        if missing:
            raise HermesAPIError(f"Hermes API is not configured: missing {', '.join(missing)}")


class HermesAPIClient:
    def __init__(
        self,
        config: HermesAPIConfig | None = None,
        session: requests.Session | None = None,
    ):
        self.config = config or HermesAPIConfig.from_env()
        self.session = session or requests.Session()

    def _headers(self) -> dict[str, str]:
        self.config.validate()
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        try:
            self.config.validate()
            url = f"{self.config.normalized_base_url()}{path}"
            response = self.session.request(
                method,
                url,
                headers=self._headers(),
                timeout=(self.config.connect_timeout, self.config.read_timeout),
                **kwargs,
            )
        except HermesAPIError:
            raise
        except (requests.RequestException, ValueError) as exc:
            raise HermesAPIError("Hermes API request could not be constructed or sent") from exc
        if response.status_code >= 400:
            try:
                payload = response.json()
                detail = payload.get("error", {}).get("message", "")
            except (ValueError, AttributeError):
                detail = "non-JSON response"
            suffix = f": {detail[:300]}" if detail else ""
            raise HermesAPIError(f"Hermes API returned {response.status_code}{suffix}")
        return response

    def _json(self, response: requests.Response, endpoint: str) -> Any:
        try:
            return response.json()
        except (ValueError, TypeError) as exc:
            raise HermesAPIError(
                f"Hermes API {endpoint} returned a non-JSON response; "
                "HERMES_API_URL must point to the API Server, not the Dashboard"
            ) from exc

    def list_models(self) -> list[dict[str, Any]]:
        payload = self._json(self._request("GET", "/v1/models"), "/v1/models")
        models = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            raise HermesAPIError("Hermes API returned an invalid /v1/models response")
        return models

    def run_task(self, task: str) -> dict[str, Any]:
        """Run one explicit Lin-requested task through official /v1/responses.

        ``store`` is false because Phase 2 intentionally does not make Hermes
        the owner of Lin's long-term memory or conversation state.
        """
        payload = self._json(
            self._request(
                "POST",
                "/v1/responses",
                json={
                    "model": self.config.model,
                    "input": task,
                    "store": False,
                    "stream": False,
                },
            ),
            "/v1/responses",
        )
        return parse_response(payload)


def parse_response(payload: Any) -> dict[str, Any]:
    """Extract final assistant text and completed server-side tool summaries."""
    if not isinstance(payload, dict) or payload.get("object") != "response":
        raise HermesAPIError("Hermes API returned an invalid /v1/responses response")

    output = payload.get("output")
    if not isinstance(output, list):
        raise HermesAPIError("Hermes API response did not include output")

    text_parts: list[str] = []
    tool_calls: list[dict[str, str]] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "message":
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text":
                    text = content.get("text")
                    if isinstance(text, str) and text:
                        text_parts.append(text)
        elif item_type == "function_call":
            name = item.get("name")
            if isinstance(name, str) and name:
                tool_calls.append({"name": name, "status": str(item.get("status") or "completed")})

    result = "\n".join(text_parts).strip()
    if not result:
        raise HermesAPIError("Hermes API response did not include final assistant text")

    return {
        "response_id": payload.get("id"),
        "status": payload.get("status", "completed"),
        "model": payload.get("model"),
        "result": result,
        "tool_calls": tool_calls,
    }
