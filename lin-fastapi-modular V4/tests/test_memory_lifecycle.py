import unittest
from unittest.mock import patch

from app.memory_rules import parse_memory_decision
from app.state import AppState


class MemoryLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.state = AppState.__new__(AppState)
        self.state.memory_bank = [
            {
                "id": 101,
                "tag": "喜好",
                "category": "长期记忆",
                "content": "Anna 喜欢喝奶茶。",
                "importance": 3,
                "keyword": "milk_tea",
                "expires_at": None,
                "created_by": "agent",
                "archived": False,
            },
            {
                "id": 202,
                "tag": "喜好",
                "category": "长期记忆",
                "content": "Anna 喜欢猫。",
                "importance": 3,
                "keyword": "cat",
                "expires_at": None,
                "created_by": "agent",
                "archived": False,
            },
        ]

    def decision(self, action, memory_id=None, summary="Anna 喜欢喝奶茶。"):
        return {
            "action": action,
            "memory_id": memory_id,
            "importance": 3,
            "category": "长期记忆",
            "tag": "喜好",
            "keyword": "milk_tea",
            "summary": summary,
        }

    @patch("app.memory_conflict.db.reinforce_memory", return_value=True)
    @patch("app.memory_conflict.db.find_memory_by_id")
    def test_same_fact_reinforces_retrieved_memory(self, find_by_id, _reinforce):
        find_by_id.return_value = dict(self.state.memory_bank[0])
        result = self.state.apply_memory_decision(
            self.decision("reinforce", 101, "Anna 最近还是很喜欢喝奶茶。")
        )
        self.assertTrue(result["success"])
        self.assertEqual("reinforced", result["action_taken"])
        self.assertEqual(101, result["memory_id"])

    @patch("app.state.db.update_memory", return_value=True)
    @patch("app.state.db.find_memory_by_id")
    def test_changed_fact_updates_explicit_retrieved_memory(self, find_by_id, _update):
        find_by_id.return_value = dict(self.state.memory_bank[0])
        result = self.state.apply_memory_decision(
            self.decision("update", 101, "Anna 现在已经很少喝奶茶了。")
        )
        self.assertEqual("updated", result["action_taken"])
        self.assertEqual("Anna 现在已经很少喝奶茶了。", self.state.memory_bank[0]["content"])

    @patch("app.memory_conflict.db.insert_memory", return_value={"success": True, "memory_id": 303, "error_reason": None})
    @patch("app.memory_conflict.db.find_memory_by_id")
    def test_obvious_contradiction_creates_pending_review(self, find_by_id, _insert):
        find_by_id.return_value = dict(self.state.memory_bank[1])
        result = self.state.apply_memory_decision(
            {**self.decision("conflict", 202, "Anna 其实不太喜欢猫，更喜欢狗。"), "keyword": "cat"}
        )
        self.assertEqual("pending_review", result["action_taken"])
        self.assertEqual(202, result["conflict_with"])

    @patch("app.state.db.archive_memory", return_value=True)
    @patch("app.state.db.find_memory_by_id")
    def test_explicitly_invalid_fact_archives_memory(self, find_by_id, _archive):
        find_by_id.return_value = dict(self.state.memory_bank[0])
        result = self.state.apply_memory_decision(
            self.decision("archive", 101, "Anna 明确表示已经不再喝奶茶。")
        )
        self.assertEqual("archived", result["action_taken"])
        self.assertEqual([202], [memory["id"] for memory in self.state.memory_bank])

    def test_unrelated_or_uncertain_information_does_not_mutate_memory(self):
        result = self.state.apply_memory_decision(self.decision("none", summary="今天看到一只猫很可爱。"))
        self.assertTrue(result["success"])
        self.assertEqual("skipped", result["action_taken"])
        self.assertEqual("lifecycle_none", result["skip_reason"])
        self.assertEqual(2, len(self.state.memory_bank))

    def test_lifecycle_actions_require_a_candidate_id(self):
        reasoning = """[MEMORY_DECISION]
worth_remembering: yes
action: update
importance: 3
category: 长期记忆
tag: 喜好
keyword: milk_tea
summary: Anna 现在很少喝奶茶。
[/MEMORY_DECISION]"""
        self.assertIsNone(parse_memory_decision(reasoning))


if __name__ == "__main__":
    unittest.main()
