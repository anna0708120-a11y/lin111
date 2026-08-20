import json
import unittest
from unittest.mock import patch

from app.integration.hermes_api import HermesAPIError, HermesConfig, list_models, run_task


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


class HermesAPITests(unittest.TestCase):
    def setUp(self):
        self.config = HermesConfig(
            base_url="https://hermes.example",
            api_key="test-secret",
            timeout_seconds=2,
            poll_interval_seconds=0,
            max_wait_seconds=2,
        )

    def test_models_uses_bearer_and_returns_payload(self):
        with patch("app.integration.hermes_api.urlopen", return_value=_Response({"data": [{"id": "hermes-agent"}]})) as call:
            result = list_models(self.config)
        self.assertEqual(result["data"][0]["id"], "hermes-agent")
        request = call.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
        self.assertEqual(request.full_url, "https://hermes.example/v1/models")

    def test_run_task_polls_and_returns_final_result(self):
        responses = [
            _Response({"run_id": "run_1", "status": "started"}),
            _Response({"run_id": "run_1", "status": "running"}),
            _Response({"run_id": "run_1", "status": "completed", "output": "Search result"}),
        ]
        with patch("app.integration.hermes_api.urlopen", side_effect=responses) as call:
            result = run_task("Search for the latest Hermes release", config=self.config)
        self.assertEqual(result["result"], "Search result")
        self.assertEqual(call.call_count, 3)
        submitted = json.loads(call.call_args_list[0].args[0].data)
        self.assertEqual(submitted["input"], "Search for the latest Hermes release")

    def test_terminal_failure_is_controlled(self):
        responses = [
            _Response({"run_id": "run_2", "status": "started"}),
            _Response({"run_id": "run_2", "status": "failed", "error": "provider unavailable"}),
        ]
        with patch("app.integration.hermes_api.urlopen", side_effect=responses):
            with self.assertRaisesRegex(HermesAPIError, "provider unavailable"):
                run_task("Search", config=self.config)


if __name__ == "__main__":
    unittest.main()
