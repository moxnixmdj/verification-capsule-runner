from __future__ import annotations

import ast
import inspect
import textwrap
import unittest
from types import SimpleNamespace

from canonical.runtime.harbor_environment_transport_v2 import (
    HarborEnvironmentTransport,
    HarborTransportError,
    HarborTransportUncertainError,
)
from canonical.runtime import harbor_science_agent_v5 as agent


class FakeEnvironment:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = 0

    async def exec(self, command, **kwargs):
        self.calls += 1
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class HarborTransportUncertaintyTests(unittest.IsolatedAsyncioTestCase):
    async def test_nonzero_returncode_is_ordinary_receipt(self):
        env = FakeEnvironment(SimpleNamespace(return_code=7, stdout="x", stderr="bad"))
        receipt = await HarborEnvironmentTransport(env).exec("false", timeout_sec=10)
        self.assertEqual(receipt.returncode, 7)
        self.assertEqual(env.calls, 1)

    async def test_exec_exception_after_dispatch_is_uncertain(self):
        env = FakeEnvironment(RuntimeError("transport lost"))
        with self.assertRaisesRegex(
            HarborTransportUncertainError,
            "EXEC_OUTCOME_UNCERTAIN",
        ):
            await HarborEnvironmentTransport(env).exec("echo x", timeout_sec=10)
        self.assertEqual(env.calls, 1)

    async def test_missing_returncode_is_uncertain(self):
        env = FakeEnvironment(SimpleNamespace(stdout="x", stderr=""))
        with self.assertRaisesRegex(
            HarborTransportUncertainError,
            "RETURNCODE_INVALID",
        ):
            await HarborEnvironmentTransport(env).exec("echo x", timeout_sec=10)
        self.assertEqual(env.calls, 1)

    async def test_pre_dispatch_validation_failure_is_not_uncertain(self):
        env = FakeEnvironment(SimpleNamespace(return_code=0, stdout="", stderr=""))
        with self.assertRaisesRegex(HarborTransportError, "TIMEOUT_INVALID"):
            await HarborEnvironmentTransport(env).exec("echo x", timeout_sec=3601)
        self.assertEqual(env.calls, 0)


class AgentUncertaintyShapeTests(unittest.TestCase):
    @staticmethod
    def _run_goal_tree():
        source = textwrap.dedent(inspect.getsource(agent.run_science_goal))
        return ast.parse(source), source

    def test_uncertainty_handlers_fault_then_return_without_replay(self):
        tree, source = self._run_goal_tree()
        handlers = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ExceptHandler)
            and isinstance(node.type, ast.Name)
            and node.type.id == "HarborTransportUncertainError"
        ]
        self.assertEqual(len(handlers), 2)
        for handler in handlers:
            handler_tree = ast.Module(body=handler.body, type_ignores=[])
            calls = [
                node for node in ast.walk(handler_tree)
                if isinstance(node, ast.Call)
            ]
            call_names = []
            for call in calls:
                fn = call.func
                if isinstance(fn, ast.Name):
                    call_names.append(fn.id)
                elif isinstance(fn, ast.Attribute):
                    call_names.append(fn.attr)
            self.assertIn("journal_fault", call_names)
            self.assertTrue(any(isinstance(node, ast.Return) for node in ast.walk(handler_tree)))
            # No effect or verification dispatch is legal inside an uncertainty handler.
            for call in calls:
                fn = call.func
                if isinstance(fn, ast.Attribute) and fn.attr == "exec":
                    self.fail("transport.exec replay found inside uncertainty handler")
        self.assertIn("BLOCKED_ACTION_EFFECT_OUTCOME_UNCERTAIN", source)
        self.assertIn("BLOCKED_VERIFICATION_OUTCOME_UNCERTAIN", source)

    def test_outer_agent_contains_exception_after_start_barrier_only(self):
        source = textwrap.dedent(inspect.getsource(agent.HarborScienceAgent.run))
        tree = ast.parse(source)
        self.assertLess(
            source.index("await start_barrier.await_start_commit"),
            source.index("try:"),
        )
        handlers = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ExceptHandler)
            and isinstance(node.type, ast.Name)
            and node.type.id == "Exception"
        ]
        self.assertGreaterEqual(len(handlers), 1)
        self.assertIn("BLOCKED_INTERNAL_CONTROLLER_OR_TRANSPORT_EXCEPTION", source)
        self.assertNotIn("except BaseException", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
