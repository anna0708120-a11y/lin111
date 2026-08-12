import inspect
import unittest

from app.agent import brain


class HermesGemmaExecutionBoundaryTests(unittest.TestCase):
    def test_render_chat_pipeline_does_not_execute_gemma(self):
        source = inspect.getsource(brain)
        self.assertNotIn("app.life.gemma_interpreter", source)
        self.assertNotIn("interpret_life_evidence(", source)

    def test_render_gemma_contract_module_is_retained(self):
        from app.life import gemma_interpreter
        self.assertTrue(callable(gemma_interpreter.interpret_life_evidence))


if __name__ == "__main__":
    unittest.main()
