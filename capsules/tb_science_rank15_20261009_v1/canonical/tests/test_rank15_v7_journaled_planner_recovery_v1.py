from __future__ import annotations

import ast
import hashlib
import inspect
import textwrap
import unittest
from unittest.mock import patch

from canonical.runtime import harbor_science_agent_v7 as agent


class V7CompositionTests(unittest.TestCase):
    def test_exact_components_are_composed(self):
        self.assertTrue(agent.science_planner.__name__.endswith("harbor_science_planner_v4"))
        self.assertEqual(agent.SCHEMA, "PROJECT_BRAIN_HARBOR_SCIENCE_AGENT_TRACE_V7")
        self.assertEqual(agent.HarborScienceAgent().version(), "1.8.0")

    def test_planner_transport_retry_is_live_through_v7(self):
        planner = agent.science_planner
        calls = []
        payload, meta = planner.build_request_payload(
            "goal", logical_attempt_id="a" * 64, cycle=1
        )
        payload_sha = hashlib.sha256(planner._payload_bytes(payload)).hexdigest()

        def fake(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                try:
                    raise TimeoutError("loopback reset")
                except TimeoutError as cause:
                    raise planner.SciencePlannerError(
                        "SCIENCE_PLANNER_LOCAL_ROUTE_FAILED:TimeoutError:loopback reset"
                    ) from cause
            return {
                "request_identity_sha256": meta["request_identity_sha256"],
                "payload_sha256": payload_sha,
            }

        with patch.object(planner, "_plan_once", fake), patch.object(
            planner.time, "sleep", lambda *_: None
        ):
            out = planner.plan(
                "goal", logical_attempt_id="a" * 64, cycle=1, timeout_s=300
            )

        self.assertEqual(len(calls), 2)
        self.assertEqual(out["transport_attempts"], 2)
        self.assertEqual(out["transport_retries"], 1)

    def test_journal_intent_precedes_environment_dispatch_in_source(self):
        source = textwrap.dedent(inspect.getsource(agent.run_science_goal))
        self.assertLess(
            source.index('"PLANNER_PROPOSAL_ACTION_INTENT"'),
            source.index('action_receipt = await transport.exec'),
        )
        self.assertIn('"ACTION_VERIFY_STATE_COMMIT"', source)

    def test_start_barrier_precedes_journal_session_and_controller(self):
        source = textwrap.dedent(inspect.getsource(agent.HarborScienceAgent.run))
        self.assertLess(
            source.index("await start_barrier.await_start_commit"),
            source.index("causal_bridge.JournalSession"),
        )
        self.assertLess(
            source.index("causal_bridge.JournalSession"),
            source.index("result = await run_science_goal"),
        )

    def test_uncertain_effect_handler_never_dispatches_recovery_effect_or_verifier(self):
        source = textwrap.dedent(inspect.getsource(agent.run_science_goal))
        tree = ast.parse(source)
        handlers = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ExceptHandler)
            and isinstance(node.type, ast.Name)
            and node.type.id == "HarborTransportUncertainError"
        ]
        self.assertEqual(len(handlers), 2)
        for handler in handlers:
            subtree = ast.Module(body=handler.body, type_ignores=[])
            calls = [n for n in ast.walk(subtree) if isinstance(n, ast.Call)]
            for call in calls:
                fn = call.func
                if isinstance(fn, ast.Attribute) and fn.attr == "exec":
                    self.fail("transport.exec replay found inside uncertainty handler")
        self.assertIn("BLOCKED_ACTION_EFFECT_OUTCOME_UNCERTAIN", source)
        self.assertIn("BLOCKED_VERIFICATION_OUTCOME_UNCERTAIN", source)

    def test_semantic_planner_failure_still_has_no_retry(self):
        planner = agent.science_planner
        calls = []

        def fake(*args, **kwargs):
            calls.append(1)
            raise planner.SciencePlannerError("SCIENCE_PLANNER_RESPONSE_JSON_INVALID")

        with patch.object(planner, "_plan_once", fake), patch.object(
            planner.time, "sleep", lambda *_: None
        ):
            with self.assertRaisesRegex(
                planner.SciencePlannerError, "RESPONSE_JSON_INVALID"
            ):
                planner.plan(
                    "goal", logical_attempt_id="b" * 64, cycle=0, timeout_s=300
                )
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
