from __future__ import annotations
import hashlib
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from canonical.runtime import harbor_environment_transport_v2 as transport
from canonical.runtime import harbor_science_planner_v4 as planner


class PlannerRetryTests(unittest.TestCase):
    def success(self, prompt, logical_attempt_id, cycle):
        payload, meta = planner.build_request_payload(
            prompt, logical_attempt_id=logical_attempt_id, cycle=cycle
        )
        return {
            "request_identity_sha256": meta["request_identity_sha256"],
            "payload_sha256": hashlib.sha256(planner._payload_bytes(payload)).hexdigest(),
        }

    def test_transport_retry_exact_identity(self):
        calls = []
        expected = self.success("goal", "1" * 64, 2)
        def fake(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                try:
                    raise TimeoutError("reset")
                except TimeoutError as cause:
                    raise planner.SciencePlannerError(
                        "SCIENCE_PLANNER_LOCAL_ROUTE_FAILED:TimeoutError:reset"
                    ) from cause
            return dict(expected)
        with patch.object(planner, "_plan_once", fake), patch.object(
            planner.time, "sleep", lambda *_: None
        ):
            out = planner.plan("goal", logical_attempt_id="1" * 64, cycle=2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(out["transport_retries"], 1)

    def test_semantic_failure_no_retry(self):
        calls = []
        def fake(*args, **kwargs):
            calls.append(1)
            raise planner.SciencePlannerError("SCIENCE_PLANNER_RESPONSE_JSON_INVALID")
        with patch.object(planner, "_plan_once", fake), patch.object(
            planner.time, "sleep", lambda *_: None
        ):
            with self.assertRaisesRegex(planner.SciencePlannerError, "RESPONSE_JSON_INVALID"):
                planner.plan("goal", logical_attempt_id="2" * 64, cycle=0)
        self.assertEqual(len(calls), 1)

    def test_identity_drift_fails_closed(self):
        calls = []
        expected = self.success("goal", "3" * 64, 1)
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
            with self.assertRaisesRegex(planner.SciencePlannerError, "RETRY_IDENTITY_DRIFT"):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
