"""Phase 3A: keyword-based chat memory retrieval tests."""
import unittest

from app.state import AppState


class MemoryRetrievalTests(unittest.TestCase):
    def setUp(self):
        # Avoid AppState.__init__ so the test has no Supabase or runtime dependencies.
        self.state = AppState.__new__(AppState)
        self.state.memory_bank = [
            {
                "category": "饮食",
                "tag": "咖啡习惯",
                "content": "Anna 最近开始喝咖啡。",
                "importance": 3,
                "keyword": "coffee",
                "archived": False,
            },
            {
                "category": "喜好",
                "tag": "电影",
                "content": "Anna 喜欢看悬疑电影。",
                "importance": 5,
                "keyword": "movie",
                "archived": False,
            },
            {
                "category": "长期记忆",
                "tag": "旧记忆",
                "content": "这条已归档，不应该出现在 prompt。",
                "importance": 5,
                "keyword": "coffee",
                "archived": True,
            },
        ]

    def test_synonym_keyword_match_returns_only_relevant_memory(self):
        result = self.state.relevant_memory_text("Anna说：我最近開始喝咖啡")

        self.assertIn("咖啡习惯", result)
        self.assertNotIn("悬疑电影", result)
        self.assertNotIn("已归档", result)

    def test_no_match_returns_empty_text(self):
        self.assertEqual(self.state.relevant_memory_text("Anna说：今天要去海边"), "")

    def test_relevance_beats_importance(self):
        result = self.state.relevant_memory_text("Anna说：咖啡让我睡不着")

        self.assertIn("咖啡习惯", result)
        self.assertNotIn("悬疑电影", result)


if __name__ == "__main__":
    unittest.main()
