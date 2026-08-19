from __future__ import annotations

import pytest

from app.integrations.hermes_api import (
    HermesAPIClient,
    HermesAPIConfig,
    HermesAPIError,
    parse_response,
)


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response


def _response_payload():
    return {
        "id": "resp_phase2",
        "object": "response",
        "status": "completed",
        "model": "configured-model",
        "output": [
            {
                "type": "function_call",
                "name": "web_search",
                "status": "completed",
                "arguments": "{\"query\": \"Hermes Agent\"}",
            },
            {
                "type": "function_call_output",
                "status": "completed",
                "call_id": "call_1",
                "output": "search result",
            },
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Search completed."}],
            },
        ],
    }


def test_client_uses_official_responses_endpoint_and_configured_model():
    session = FakeSession(FakeResponse(_response_payload()))
    config = HermesAPIConfig("https://hermes.example", "api-key", "configured-model")

    result = HermesAPIClient(config, session=session).run_task("Search for Hermes Agent news")

    method, url, kwargs = session.calls[0]
    assert method == "POST"
    assert url == "https://hermes.example/v1/responses"
    assert kwargs["headers"]["Authorization"] == "Bearer api-key"
    assert kwargs["json"] == {
        "model": "configured-model",
        "input": "Search for Hermes Agent news",
        "store": False,
        "stream": False,
    }
    assert result["result"] == "Search completed."
    assert result["tool_calls"] == [{"name": "web_search", "status": "completed"}]


def test_list_models_uses_official_models_endpoint():
    session = FakeSession(FakeResponse({"object": "list", "data": [{"id": "configured-model"}]}))
    config = HermesAPIConfig("https://hermes.example", "api-key", "configured-model")

    assert HermesAPIClient(config, session=session).list_models() == [{"id": "configured-model"}]
    assert session.calls[0][1] == "https://hermes.example/v1/models"


def test_base_url_normalization_accepts_root_and_v1_forms():
    assert HermesAPIConfig("https://hermes.example/", "k", "m").normalized_base_url() == "https://hermes.example"
    assert HermesAPIConfig("https://hermes.example/v1", "k", "m").normalized_base_url() == "https://hermes.example"
    assert HermesAPIConfig("https://hermes.example/api/v1/", "k", "m").normalized_base_url() == "https://hermes.example/api"


def test_base_url_rejects_non_http_or_query_urls():
    for value in ("hermes.example", "https://hermes.example?x=1", "https://"):
        with pytest.raises(HermesAPIError, match="HERMES_API_URL"):
            HermesAPIConfig(value, "k", "m").normalized_base_url()


def test_client_converts_non_json_success_response():
    class HtmlResponse(FakeResponse):
        def json(self):
            raise ValueError("not JSON")

    session = FakeSession(HtmlResponse("<html>Dashboard</html>"))
    config = HermesAPIConfig("https://hermes.example", "secret-value", "configured-model")
    with pytest.raises(HermesAPIError, match="not the Dashboard"):
        HermesAPIClient(config, session=session).list_models()


def test_parse_response_rejects_missing_final_text():
    with pytest.raises(HermesAPIError, match="final assistant text"):
        parse_response({"object": "response", "output": []})


def test_client_rejects_missing_configuration():
    with pytest.raises(HermesAPIError, match="HERMES_MODEL"):
        HermesAPIClient(HermesAPIConfig("https://hermes.example", "api-key", "")).run_task("hello")


def test_client_converts_official_api_errors_without_exposing_key():
    session = FakeSession(
        FakeResponse({"error": {"message": "Invalid gateway API key"}}, status_code=401)
    )
    config = HermesAPIConfig("https://hermes.example", "secret-value", "configured-model")

    with pytest.raises(HermesAPIError, match="returned 401: Invalid gateway API key"):
        HermesAPIClient(config, session=session).run_task("hello")


def test_task_route_is_independent_and_returns_completed_agent_result(monkeypatch):
    from fastapi.testclient import TestClient
    from app.integrations import hermes_api_routes
    from app.main import app

    class FakeClient:
        def run_task(self, task):
            assert task == "Search current Hermes Agent news"
            return {
                "response_id": "resp_phase2",
                "status": "completed",
                "model": "configured-model",
                "result": "Search completed.",
                "tool_calls": [{"name": "web_search", "status": "completed"}],
            }

    monkeypatch.setattr(hermes_api_routes, "_client", lambda: FakeClient())
    response = TestClient(app).post(
        "/api/hermes/task", json={"task": "Search current Hermes Agent news"}
    )

    assert response.status_code == 200
    assert response.json()["tool_calls"] == [{"name": "web_search", "status": "completed"}]


def test_task_route_converts_api_failure_to_controlled_error(monkeypatch):
    from fastapi.testclient import TestClient
    from app.integrations import hermes_api_routes
    from app.main import app

    class FailingClient:
        def run_task(self, task):
            raise HermesAPIError("Hermes API returned 401: Invalid gateway API key")

    monkeypatch.setattr(hermes_api_routes, "_client", lambda: FailingClient())
    response = TestClient(app).post("/api/hermes/task", json={"task": "Search news"})

    assert response.status_code == 502
    assert response.json()["detail"] == "Hermes API returned 401: Invalid gateway API key"
