import unittest
from unittest.mock import Mock, patch

from app import config
from app.llm.main_router import get_main_model_config, get_main_provider
from app.llm.openai_compatible import OpenAICompatibleProvider
from app.llm.provider_interface import ProviderCapabilities


class MainProviderRoutingTests(unittest.TestCase):
    def test_default_provider_is_configured_without_brain_model_ids(self):
        resolved = get_main_model_config()
        self.assertEqual(resolved["provider"], config.DEFAULT_PROVIDER)
        self.assertEqual(resolved["model"], config.DEFAULT_MODEL)
        self.assertIn("reasoning", resolved["capabilities"])
        self.assertIn("tool_calling", resolved["capabilities"])

    def test_main_providers_resolve_to_their_configured_endpoints(self):
        expected_endpoints = {
            "gpt": "https://api.a6api.com/v1",
            "claude": "https://api.a6api.com/v1",
            "deepseek": "https://api.deepseek.com",
        }
        for provider, expected_base_url in expected_endpoints.items():
            resolved = get_main_model_config(provider=provider)
            instance = get_main_provider(provider=provider)
            self.assertEqual(instance.base_url, expected_base_url)
            self.assertEqual(instance._url(), expected_base_url + "/chat/completions")
            self.assertEqual(resolved["model"], config.PROVIDER_MODELS[provider])

    def test_model_override_maps_without_changing_provider(self):
        resolved = get_main_model_config(provider="gpt", model="gpt-5.6-luna")
        self.assertEqual(resolved["provider"], "gpt")
        self.assertEqual(resolved["model"], "gpt-5.6-luna")

    @patch("app.llm.openai_compatible.requests.post")
    def test_chat_failure_returns_fallback_tuple(self, post):
        post.side_effect = RuntimeError("provider unavailable")
        provider = OpenAICompatibleProvider(
            name="gpt", api_key="test", base_url="https://api.a6api.com/v1", model="gpt-5.6-terra"
        )
        self.assertEqual(provider.chat("hello"), (None, None))

    @patch("app.llm.openai_compatible.requests.post")
    def test_stream_failure_returns_error_event(self, post):
        post.side_effect = RuntimeError("provider unavailable")
        provider = OpenAICompatibleProvider(
            name="claude", api_key="test", base_url="https://api.a6api.com/v1", model="claude-sonnet-5"
        )
        self.assertEqual(list(provider.stream_chat("hello")), [("error", "provider unavailable")])

    @patch("app.llm.openai_compatible.requests.post")
    def test_chat_parses_content_and_reasoning(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": "reply", "reasoning_content": "reason"}}]
        }
        post.return_value = response
        provider = OpenAICompatibleProvider(
            name="deepseek", api_key="test", base_url="https://api.a6api.com/v1", model="deepseek-v4-flash"
        )
        self.assertEqual(provider.chat("hello"), ("reply", "reason"))
        self.assertEqual(post.call_args.args[0], "https://api.a6api.com/v1/chat/completions")


if __name__ == "__main__":
    unittest.main()
