import unittest
from unittest.mock import patch

from app import agent
from app.agent import brain


class ProactiveBrainRegressionTests(unittest.TestCase):
    @patch.object(brain.state, "check_rate_limit", return_value=True)
    @patch.object(brain.state, "get_recent_conversation", return_value=[])
    @patch.object(brain.state, "recent_memory_text", return_value="")
    @patch.object(brain.state, "get_main_model", return_value={"provider": "deepseek", "model": "deepseek-v4-flash"})
    def test_non_streaming_generation_uses_current_prompt_pipeline(
        self, _model, _memory, _conversation, _rate_limit
    ):
        with patch.object(brain, "chat_main_model", return_value=("低风险测试回复", None)) as chat:
            reply, thinking = brain.generate_reply("这是 proactive regression test", use_cache=False)

        self.assertEqual(reply, "低风险测试回复")
        self.assertIsNone(thinking)
        chat.assert_called_once()
        self.assertIn("我是某款AI模型", chat.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
