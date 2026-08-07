import unittest
from unittest.mock import patch

from app import db
from app.memory_conflict import handle_memory_with_conflict_check
from app.memory_rules import parse_memory_decision
from app.state import AppState

SAMPLE = '''[MEMORY_DECISION]
worth_remembering: yes
importance: 4
category: 长期记忆
tag: 偏好
keyword: 喜欢狗
summary: Anna 喜欢狗。
action: create
[/MEMORY_DECISION]'''


class FakeInsert:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return type("Response", (), {"data": self.data})()


class FakeTable:
    def __init__(self, data):
        self.data = data

    def insert(self, _payload):
        return FakeInsert(self.data)


class FakeClient:
    def __init__(self, data):
        self.data = data

    def table(self, name):
        self.name = name
        return FakeTable(self.data)


class MemoryObservabilityTests(unittest.TestCase):
    def test_parse_explicit_dog_preference(self):
        decision = parse_memory_decision(SAMPLE)
        self.assertEqual(decision["action"], "create")
        self.assertEqual(decision["summary"], "Anna 喜欢狗。")

    def test_insert_memory_reports_missing_client(self):
        with patch.object(db, "_client", None):
            result = db.insert_memory("偏好", "Anna 喜欢狗。")
        self.assertEqual(result, {
            "success": False,
            "memory_id": None,
            "error_reason": "Supabase client missing",
        })

    def test_insert_memory_reports_inserted_id(self):
        with patch.object(db, "_client", FakeClient([{"id": 42}])):
            result = db.insert_memory("偏好", "Anna 喜欢狗。")
        self.assertEqual(result["success"], True)
        self.assertEqual(result["memory_id"], 42)
        self.assertIsNone(result["error_reason"])

    def test_remember_adds_memory_bank_only_after_success(self):
        decision = parse_memory_decision(SAMPLE)
        state = AppState.__new__(AppState)
        state.memory_bank = []
        with patch("app.memory_conflict.detect_conflict", return_value={
            "action": "create", "conflicting_memory": None,
        }), patch("app.memory_conflict.db.insert_memory", return_value={
            "success": True, "memory_id": 42, "error_reason": None,
        }):
            result = state.remember_or_reinforce(decision)
        self.assertEqual(result["memory_id"], 42)
        self.assertEqual(len(state.memory_bank), 1)
        self.assertEqual(state.memory_bank[0]["content"], "Anna 喜欢狗。")

    def test_remember_does_not_add_memory_bank_after_failure(self):
        decision = parse_memory_decision(SAMPLE)
        state = AppState.__new__(AppState)
        state.memory_bank = []
        with patch("app.memory_conflict.detect_conflict", return_value={
            "action": "create", "conflicting_memory": None,
        }), patch("app.memory_conflict.db.insert_memory", return_value={
            "success": False, "memory_id": None, "error_reason": "Supabase client missing",
        }):
            result = state.remember_or_reinforce(decision)
        self.assertEqual(result["skip_reason"], "Supabase client missing")
        self.assertEqual(state.memory_bank, [])


if __name__ == "__main__":
    unittest.main()
