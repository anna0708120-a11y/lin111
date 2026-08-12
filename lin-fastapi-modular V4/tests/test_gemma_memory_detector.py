import unittest
from unittest.mock import Mock, patch

from app.llm import groq_memory_detector as detector


class GemmaMemoryDetectorTests(unittest.TestCase):
    def test_coarse_gate_rejects_one_off_event(self):
        self.assertFalse(detector.coarse_memory_candidate("我今天在咖啡店看到一只狗"))

    @patch.object(detector.config, "GEMMA_MODEL", "gemma4:31b")
    @patch.object(detector.config, "GEMMA_API_KEY", "test-key")
    @patch.object(detector.requests, "post")
    def test_gemma_returns_structured_remember_candidate(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "message": {"content": '{"decision":"remember","tag":"喜好","keyword":"喜欢狗","summary":"Anna喜欢狗","reason":"明确偏好"}'}
        }
        post.return_value = response

        result = detector.detect_memory_candidate("我喜欢狗")

        self.assertEqual(result["decision"], "remember")
        self.assertEqual(result["summary"], "Anna喜欢狗")
        self.assertEqual(post.call_args.args[0], "https://ollama.com/api/chat")
        self.assertEqual(post.call_args.kwargs["json"]["model"], "gemma4:31b")
        self.assertFalse(post.call_args.kwargs["json"]["stream"])

    @patch.object(detector.config, "GEMMA_API_KEY", "")
    def test_missing_gemma_key_is_uncertain_for_non_explicit_candidate(self):
        result = detector.detect_memory_candidate("我喜欢狗")
        self.assertEqual(result["decision"], "uncertain")


if __name__ == "__main__":
    unittest.main()
