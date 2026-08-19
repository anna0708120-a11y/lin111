"""Independent Lin endpoint for explicit Hermes Agent tasks.

This is intentionally separate from Lin's /watch → brain.py chat path.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.integrations.hermes_api import HermesAPIClient, HermesAPIError, HermesAPIConfig


router = APIRouter(prefix="/api/hermes", tags=["hermes-agent"])


class HermesTaskPayload(BaseModel):
    task: str = Field(min_length=1, max_length=32_000)


def _client() -> HermesAPIClient:
    return HermesAPIClient()


@router.get("/status")
def hermes_api_status() -> dict[str, Any]:
    config = HermesAPIConfig.from_env()
    configured = all((config.base_url, config.api_key, config.model))
    return {"configured": configured}


@router.get("/models")
def hermes_models() -> dict[str, Any]:
    try:
        return {"data": _client().list_models()}
    except HermesAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/task")
def run_hermes_task(payload: HermesTaskPayload) -> dict[str, Any]:
    """Run an explicit task in Hermes without altering Lin's chat pipeline."""
    try:
        return _client().run_task(payload.task)
    except HermesAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
