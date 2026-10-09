from __future__ import annotations
import asyncio
import hashlib
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from canonical.runtime import harbor_environment_transport_v2 as transport
from canonical.runtime import harbor_science_agent_v6 as agent
from canonical.runtime import harbor_science_planner_v4 as planner


class PlannerRetryTests(unittest.TestCase):
    def _success(self, prompt, logical_attempt_id, cycle):
        payload, meta = planner.build_request_payload(
            prompt, logical_attempt_id=logical_attempt_id, cycle=cycle
        )
        return {
            "request_identity_sha256": meta["request_identity_sha256"],
            "payload_sha256": hashlib.sha256(planner._payload_bytes(payload)).hexdigest(),
        }

    def test_transport_only_retry_keeps_exact_identity(self):
        calls = []
        expected = self._success("goal", "1" * 64, 2)

        def fake(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                try:
                    raise TimeoutError("loopback reset")
                except TimeoutError as cause:
                    raise planner.SciencePlannerError(
                        "SCIENCE_PLANNER_LOCAL_ROUTE_FAILED:TimeoutError:loopback reset"
                    ) from cause
            return dict(expected)

        with patch.object(planner, "_plan_once", fake), patch.object(
            planner.time, "sleep", lambda *_: None
        ):
            out = planner.plan("goal", logical_attempt_id="1" * 64, cycle=2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(out["transport_attempts"], 2)
        self.assertEqual(out["transport_retries"], 1)

    def test_semantic_failure_is_never_retried(self):
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
                planner.plan("goal", logical_attempt_id="2" * 64, cycle=0)
        self.assertEqual(len(calls), 1)

    def test_retry_identity_drift_fails_closed(self):
        calls = []
        expected = self._success("goal", "3" * 64, 1)

        def fake(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                try:
                    raise ConnectionError("reset")
                except ConnectionError as cause:
                    raise planner.SciencePlannerError(
                        "SCIENCE_PLANNER_LOCAL_ROUTE_FAILED:ConnectionError:reset"
                    ) from cause
            out = dict(expected)
            out["request_identity_sha256"] = "0" * 64
            return out

        with patch.object(planner, "_plan_once", fake), patch.object(
            planner.time, "sleep", lambda *_: None
        ):
            with self.assertRaisesRegex(
                planner.SciencePlannerError, "RETRY_IDENTITY_DRIFT"
            ):
                planner.plan("goal", logical_attempt_id="3" * 64, cycle=1)
        self.assertEqual(len(calls), 2)


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_dispatch_exception_is_uncertain(self):
        class Env:
            async def exec(self, *args, **kwargs):
                raise RuntimeError("lost receipt")

        with self.assertRaises(transport.HarborTransportUncertainError):
            await transport.HarborEnvironmentTransport(Env()).exec("echo x")

    async def test_missing_returncode_is_uncertain(self):
        class Env:
            async def exec(self, *args, **kwargs):
                return SimpleNamespace(stdout="x", stderr="")

        with self.assertRaises(transport.HarborTransportUncertainError):
            await transport.HarborEnvironmentTransport(Env()).exec("echo x")

    async def test_nonzero_returncode_is_observed(self):
        class Env:
            async def exec(self, *args, **kwargs):
                return SimpleNamespace(returncode=7, stdout="", stderr="bad")

        receipt = await transport.HarborEnvironmentTransport(Env()).exec("false")
        self.assertEqual(receipt.returncode, 7)


class AgentReconciliationTests(unittest.IsolatedAsyncioTestCase):
    async def test_uncertain_effect_is_never_replayed_and_verifier_can_reconcile(self):
        calls = []

        class Env:
            async def exec(self, command, timeout_sec=None, **kwargs):
                calls.append(command)
                if command == "effect":
                    raise RuntimeError("receipt lost")
                if command == "check":
                    return SimpleNamespace(returncode=0, stdout="proved", stderr="")
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

        def plan(*args, **kwargs):
            return {
                "text": json.dumps(
                    {
                        "material_requirements": ["R1"],
                        "candidates": [
                            {
                                "action_id": "A1",
                                "covers": ["R1"],
                                "command": "effect",
                                "verify_command": "check",
                            }
                        ],
                    }
                ),
                "model": "synthetic",
            }

        with patch.object(agent.science_planner, "plan", plan), patch.object(\n            agent.science_planner, "count_input_tokens", lambda payload: 1000\n        ):\n            out = await agent.run_science_goal("Create result.", Env(), max_cycles=1)\n
        self.assertEqual(calls.count("effect"), 1)
        self.assertEqual(calls.count("check"), 1)
        row = [x for x in out["trace"] if x.get("kind") == "BRAIN_SELECTED_RESEARCH_ACTION"][0]
        self.assertFalse(row["effect_replayed"])
        self.assertTrue(row["uncertain_action_reconciled_by_existing_verifier"])

    async def test_unreconciled_uncertain_effect_blocks_without_replay(self):
        calls = []

        class Env:
            async def exec(self, command, timeout_sec=None, **kwargs):
                calls.append(command)
                if command == "effect":
                    raise RuntimeError("receipt lost")
                if command == "check":
                    return SimpleNamespace(returncode=1, stdout="", stderr="not proved")
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

        def plan(*args, **kwargs):
            return {
                "text": json.dumps(
                    {
                        "material_requirements": ["R1"],
                        "candidates": [
                            {
                                "action_id": "A1",
                                "covers": ["R1"],
                                "command": "effect",
                                "verify_command": "check",
                            }
                        ],
                    }
                ),
                "model": "synthetic",
            }

        with patch.object(agent.science_planner, "plan", plan):
            out = await agent.run_science_goal("Create result.", Env(), max_cycles=1)

        self.assertEqual(calls.count("effect"), 1)
        self.assertEqual(calls.count("check"), 1)
        self.assertEqual(out["status"], "BLOCKED_ACTION_EFFECT_OUTCOME_UNCERTAIN")
        self.assertFalse(out["effect_replay_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
