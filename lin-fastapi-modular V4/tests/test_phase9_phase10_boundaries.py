import unittest

from app.life.mcp_registry import Capability, CapabilityRegistry, registry
from app.life.tool_brain import run_backend_suggestion, run_suggestion
from app.life.tool_executor import dispatch, reset_dispatch_state


class ToolBrainAndMcpTests(unittest.TestCase):
    def setUp(self):
        reset_dispatch_state()

    def test_tool_brain_only_suggests(self):
        result = run_suggestion({"route": "welcome_home"})
        self.assertFalse(result["executed"])
        self.assertEqual(result["suggestion"]["decision"], "no_tool")

    def test_backend_falls_back_without_credentials(self):
        result = run_backend_suggestion({"route": "welcome_home"})
        self.assertFalse(result["executed"])
        self.assertEqual(result["suggestion"]["decision"], "no_tool")

    def test_registry_exposes_read_only_capability(self):
        item = registry.get("web.search")
        self.assertIsNotNone(item)
        self.assertFalse(item.side_effect)

    def test_dispatch_enforces_cooldown(self):
        local = CapabilityRegistry()
        local.register(Capability(
            "read",
            "read",
            {"value": "string"},
            {"ok": "boolean"},
            cooldown_seconds=60,
            executor=lambda args: {"ok": True, "value": args["value"]},
        ))
        first = dispatch("read", {"value": "x"}, capability_registry=local)
        second = dispatch("read", {"value": "x"}, capability_registry=local)
        self.assertTrue(first["ok"])
        self.assertEqual(second["error"], "capability_cooldown")

    def test_side_effect_capability_cannot_dispatch(self):
        local = CapabilityRegistry()
        local.register(Capability(
            "write",
            "write",
            {},
            {},
            side_effect=True,
            idempotent=True,
            executor=lambda _: {"ok": True},
        ))
        result = dispatch("write", {}, capability_registry=local)
        self.assertEqual(result["error"], "side_effect_requires_life_action")

    def test_reject_non_idempotent_side_effect(self):
        local = CapabilityRegistry()
        with self.assertRaises(ValueError):
            local.register(Capability("unsafe", "write", {}, {}, side_effect=True, idempotent=False))


if __name__ == "__main__":
    unittest.main()
