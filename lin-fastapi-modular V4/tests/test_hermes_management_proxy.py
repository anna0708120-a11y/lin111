import os
from pathlib import Path

import pytest
from fastapi import HTTPException


ROOT = Path(__file__).parents[1]
import sys
sys.path.insert(0, str(ROOT))

from app.integrations import hermes_management_proxy as proxy


def test_management_proxy_migrates_legacy_agent_url_to_gateway(monkeypatch):
    monkeypatch.setenv("HERMES_MANAGEMENT_URL", "https://hermes-agent-bdd8.onrender.com")
    monkeypatch.setenv("HERMES_MANAGEMENT_TOKEN", "management-token")

    assert proxy._base_url() == "https://hermes-agent-1-i8yp.onrender.com"


def test_management_proxy_uses_gateway_token_when_management_token_is_absent(monkeypatch):
    monkeypatch.setenv("HERMES_MANAGEMENT_URL", "https://hermes-agent-1-i8yp.onrender.com")
    monkeypatch.delenv("HERMES_MANAGEMENT_TOKEN", raising=False)
    monkeypatch.setenv("HERMES_DASHBOARD_INTERNAL_TOKEN", "gateway-token")

    assert proxy._management_token() == "gateway-token"


def test_management_proxy_requires_url_and_token(monkeypatch):
    monkeypatch.delenv("HERMES_MANAGEMENT_URL", raising=False)
    monkeypatch.delenv("HERMES_MANAGEMENT_TOKEN", raising=False)
    monkeypatch.delenv("HERMES_DASHBOARD_INTERNAL_TOKEN", raising=False)

    with pytest.raises(HTTPException) as error:
        proxy._base_url()

    assert error.value.status_code == 503
