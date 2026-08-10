"""Phase 10 MCP-compatible capability registry.

This is intentionally a local registry, not an unrestricted MCP client. Every
external integration must declare capability, schemas, side effects, idempotency
and cooldown before Phase 10 dispatch can expose it to the runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Capability:
    name: str
    permission: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    side_effect: bool = False
    idempotent: bool = True
    cooldown_seconds: int = 0
    executor: Callable[[dict[str, Any]], dict[str, Any]] | None = field(default=None, compare=False, repr=False)


class CapabilityRegistry:
    def __init__(self) -> None:
        self._items: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        if capability.side_effect and not capability.idempotent:
            raise ValueError("side_effect_capability_requires_idempotency")
        if not capability.name or capability.name in self._items:
            raise ValueError("invalid_or_duplicate_capability")
        self._items[capability.name] = capability

    def get(self, name: str) -> Capability | None:
        return self._items.get(name)

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "name": item.name,
                "permission": item.permission,
                "input_schema": item.input_schema,
                "output_schema": item.output_schema,
                "side_effect": item.side_effect,
                "idempotent": item.idempotent,
                "cooldown_seconds": item.cooldown_seconds,
            }
            for item in self._items.values()
        ]


registry = CapabilityRegistry()

# Read-only capabilities are allowed to be suggested by Tool Brain. Any future
# side-effect capability must re-enter Life Candidate -> Policy -> Outbox.
from .tavily import search as tavily_search

registry.register(Capability(
    name="web.search",
    permission="read_external_data",
    input_schema={"query": "string"},
    output_schema={"results": "array", "answer": "string|null"},
    side_effect=False,
    idempotent=True,
    cooldown_seconds=30,
    executor=tavily_search,
))
