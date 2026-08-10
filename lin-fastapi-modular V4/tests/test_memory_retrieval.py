import unittest

from app.state import AppState


class MemoryRetrievalTests(unittest.TestCase):
    def make_state(self):
        state = AppState.__new__(AppState)
        state.memory_bank = [
            {"id": 1, "category": "偏好", "tag": "饮料", "content": "Anna喜欢喝咖啡。", "keyword": "coffee", "importance": 3, "archived": False},
            {"id": 2, "category": "偏好", "tag": "饮料", "content": "Anna每天早上喝咖啡。", "keyword": "coffee", "importance": 5, "archived": False},
            {"id": 3, "category": "偏好", "tag": "饮料", "content": "Anna喜欢喝茶。", "keyword": "tea", "importance": 5, "archived": False},
            {"id": 4, "category": "偏好", "tag": "宠物", "content": "Anna喜欢猫。", "keyword": "cats", "importance": 4, "archived": False},
            {"id": 5, "category": "偏好", "tag": "旧", "content": "旧咖啡记忆。", "keyword": "coffee", "importance": 2, "archived": True},
        ]
        return state

    def test_query_prioritizes_only_relevant_memories(self):
        text = self.make_state().recent_memory_text(query="Anna最近开始喝咖啡")
        self.assertIn("Anna每天早上喝咖啡。", text)
        self.assertIn("Anna喜欢喝咖啡。", text)
        self.assertNotIn("Anna喜欢喝茶。", text)
        self.assertNotIn("Anna喜欢猫。", text)
        self.assertNotIn("旧咖啡记忆。", text)

    def test_relevant_memories_use_importance_as_tiebreaker(self):
        text = self.make_state().recent_memory_text(query="Anna最近开始喝咖啡")
        self.assertLess(text.index("Anna每天早上喝咖啡。"), text.index("Anna喜欢喝咖啡。"))

    def test_query_returns_empty_when_no_memory_is_relevant(self):
        text = self.make_state().recent_memory_text(query="Anna今天去了便利店买水")
        self.assertEqual(text, "")

    def test_empty_query_preserves_bounded_importance_fallback(self):
        text = self.make_state().recent_memory_text(n=2)
        self.assertEqual(text.count("[偏好·"), 2)
        self.assertNotIn("旧咖啡记忆。", text)


if __name__ == "__main__":
    unittest.main()
