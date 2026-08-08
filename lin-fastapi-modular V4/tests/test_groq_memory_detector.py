import unittest
import unittest
from unittest.mock import Mock, patch

from app.llm import groq_memory_detector as detector


class GroqMemoryDetectorTests(unittest.TestCase):
    def test_coarse_gate_rejects_one_off_event(self):
        self.assertFalse(detector.coarse_memory_candidate("我今天在咖啡店看到一只狗"))

    def test_coarse_gate_accepts_explicit_preference(self):
        self.assertTrue(detector.coarse_memory_candidate("我喜欢狗"))

    @patch.object(detector.config, "GROQ_API_KEY", "test-key")
    @patch.object(detector.requests, "post")
    def test_groq_returns_structured_remember_candidate(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": '{"decision":"remember","tag":"喜好","keyword":"喜欢狗","summary":"Anna喜欢狗","reason":"明确偏好"}'}}]
        }
        post.return_value = response

        result = detector.detect_memory_candidate("我喜欢狗")

        self.assertEqual(result["decision"], "remember")
        self.assertEqual(result["summary"], "Anna喜欢狗")
        request = post.call_args
        self.assertEqual(request.args[0], "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(request.kwargs["json"]["model"], "openai/gpt-oss-20b")
        self.assertEqual(request.kwargs["json"]["response_format"], {"type": "json_object"})

    @patch.object(detector.config, "GROQ_API_KEY", "test-key")
    @patch.object(detector.requests, "post")
    def test_uncertain_does_not_expose_reasoning_fields(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": '{"decision":"uncertain","reason":"證據不足"}'}}]
        }
        post.return_value = response

        result = detector.detect_memory_candidate("我一直不确定自己喜不喜欢狗")

        self.assertEqual(result["decision"], "uncertain")
        self.assertEqual(result["summary"], "")
        self.assertNotIn("reasoning", result)

    @patch.object(detector.config, "GROQ_API_KEY", "")
    def test_missing_groq_key_is_uncertain_for_non_explicit_candidate(self):
        result = detector.detect_memory_candidate("我喜欢狗")
        self.assertEqual(result["decision"], "uncertain")

    def test_candidate_renders_through_existing_memory_parser_shape(self):
        text = detector.candidate_to_parser_text({
            "decision": "remember",
            "tag": "喜好",
            "keyword": "喜欢狗",
            "summary": "Anna喜欢狗",
        })
        self.assertIn("[MEMORY_DECISION]", text)
        self.assertIn("action: create", text)
        self.assertIn("summary: Anna喜欢狗", text)


if __name__ == "__main__":
    unittest.main()
