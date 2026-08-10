import unittest
import unittest
from unittest.mock import patch

from app import db
from app.llm.main_router import get_main_model_config, get_main_provider
from app.state import AppState


class MainModelSelectorTests(unittest.TestCase):
    def test_catalog_exposes_all_selectable_models(self):
        expected = {
            "gpt-5.6-terra",
            "gpt-5.6-luna",
            "gpt-5.4-mini",
            "claude-sonnet-5",
            "claude-haiku-4-5",
            "deepseek-v4-flash",
        }
        from app.llm.main_router import list_main_models
        self.assertEqual({item["model"] for item in list_main_models()}, expected)

    def test_selected_model_derives_its_provider(self):
        resolved = get_main_model_config(model="gpt-5.6-luna")
        self.assertEqual(resolved["provider"], "gpt")
        self.assertEqual(resolved["model"], "gpt-5.6-luna")
        self.assertEqual(get_main_provider(model="claude-haiku-4-5").name, "claude")

    def test_provider_model_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            get_main_model_config(provider="deepseek", model="gpt-5.6-terra")

    def test_app_state_persists_selected_main_model(self):
        state = AppState.__new__(AppState)
        with patch.object(db, "save_context") as save_context:
            selected = state.update_main_model(model="gpt-5.6-luna")
        self.assertEqual(selected["provider"], "gpt")
        self.assertEqual(selected["model"], "gpt-5.6-luna")
        save_context.assert_called_once_with("main_model", selected)


if __name__ == "__main__":
    unittest.main()
