import unittest
from unittest.mock import Mock, patch

from app import memory_intent
from app.llm import groq_memory_detector as detector


CASES = (
    ("preference", "我很喜欢猫，尤其喜欢橘猫。", "remember"),
    ("explicit_request", "记住，我以后不喝咖啡。", "remember"),
    ("one_off_event", "我今天在街上看到一只猫，觉得它挺可爱的。", "no"),
    ("counter_evidence", "今天看到一只肥猫，挺可爱的，不过它身上太脏了，我没摸。", "uncertain"),
    ("ordinary_fact", "我今天去了便利店买水。", "no"),
    ("long_term_habit", "我平时晚上睡觉前都会画一会儿画。", "remember"),
    ("temporary_emotion", "我今天心情特别好。", "no"),
    ("long_term_state", "我一直都很喜欢画画，这个兴趣很多年了。", "remember"),
    ("weak_hint", "最近总觉得咖啡很好喝。", "uncertain"),
    ("contradiction", "我以前很喜欢猫，但现在其实不太喜欢了。", "uncertain"),
)


class Phase2CMemoryDetectorTests(unittest.TestCase):
    def test_coarse_gate_keeps_only_plausible_candidates(self):
        self.assertTrue(detector.coarse_memory_candidate("我很喜欢猫，尤其喜欢橘猫。"))
        self.assertTrue(detector.coarse_memory_candidate("我平时晚上睡觉前都会画一会儿画。"))
        self.assertFalse(detector.coarse_memory_candidate("我今天在街上看到一只猫，觉得它挺可爱的。"))
        self.assertFalse(detector.coarse_memory_candidate("我今天去了便利店买水。"))
        self.assertFalse(detector.coarse_memory_candidate("我今天心情特别好。"))

    def test_explicit_request_bypasses_groq_detector(self):
        with patch.object(detector.requests, "post") as post:
            decision = memory_intent.build_memory_decision("记住，我以后不喝咖啡。")
        self.assertEqual(decision["action"], "create")
        self.assertEqual(decision["summary"], "我以后不喝咖啡")
        post.assert_not_called()

    @patch.object(detector.config, "GROQ_API_KEY", "test-key")
    @patch.object(detector.requests, "post")
    def test_groq_request_uses_structured_short_output(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": '{"decision":"remember","tag":"喜好","keyword":"喜欢猫","summary":"Anna喜欢猫，尤其喜欢橘猫","reason":"明确偏好"}'}}]
        }
        post.return_value = response

        result = detector.detect_memory_candidate("我很喜欢猫，尤其喜欢橘猫。")
        payload = post.call_args.kwargs["json"]

        self.assertEqual(result["decision"], "remember")
        self.assertEqual(payload["model"], "openai/gpt-oss-20b")
        self.assertEqual(payload["temperature"], 0.1)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertNotIn("stream", payload)
        self.assertNotIn("reasoning", result)

    def test_mocked_detector_cases_have_no_false_positives(self):
        responses = {
            "preference": {"decision": "remember", "tag": "喜好", "keyword": "喜欢猫", "summary": "Anna喜欢猫"},
            "one_off_event": {"decision": "no", "reason": "一次性事件"},
            "counter_evidence": {"decision": "uncertain", "reason": "存在反向证据"},
            "ordinary_fact": {"decision": "no", "reason": "普通一次性事实"},
            "temporary_emotion": {"decision": "no", "reason": "一次性情绪"},
            "long_term_habit": {"decision": "remember", "tag": "习惯", "keyword": "睡前画画", "summary": "Anna平时睡前会画画"},
            "long_term_state": {"decision": "remember", "tag": "兴趣", "keyword": "喜欢画画", "summary": "Anna长期喜欢画画"},
            "weak_hint": {"decision": "uncertain", "reason": "近期感受不足以证明长期偏好"},
            "contradiction": {"decision": "uncertain", "reason": "过去与现在矛盾"},
        }
        with patch.object(detector.config, "GROQ_API_KEY", "test-key"), patch.object(detector.requests, "post") as post:
            for case_id, text, expected in CASES:
                if case_id == "explicit_request":
                    continue
                response = Mock()
                response.raise_for_status.return_value = None
                response.json.return_value = {"choices": [{"message": {"content": __import__("json").dumps(responses[case_id], ensure_ascii=False)}}]}
                post.return_value = response
                result = detector.detect_memory_candidate(text)
                self.assertEqual(result["decision"], expected, case_id)
                if expected != "remember":
                    self.assertEqual(result["summary"], "", case_id)

    @patch.object(detector.config, "GROQ_API_KEY", "test-key")
    @patch.object(detector.requests, "post")
    def test_detector_error_is_uncertain_and_non_writing(self, post):
        post.side_effect = detector.requests.RequestException("timeout")
        result = detector.detect_memory_candidate("我很喜欢猫，尤其喜欢橘猫。")
        self.assertEqual(result["decision"], "uncertain")
        self.assertEqual(detector.candidate_to_parser_text(result), "")


if __name__ == "__main__":
    unittest.main()
