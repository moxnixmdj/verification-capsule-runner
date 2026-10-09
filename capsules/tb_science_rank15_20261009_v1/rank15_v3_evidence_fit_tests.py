from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import unittest
from unittest.mock import AsyncMock, patch

from canonical.runtime import harbor_science_agent_v3 as agent
from canonical.runtime import harbor_science_planner_v3 as planner
from canonical.runtime.harbor_science_evidence_frontier_v1 import EvidenceLedger


LOGICAL = "d" * 64


class EvidenceFitTests(unittest.TestCase):
    def _fit(self, ledger: EvidenceLedger, requested=None):
        return agent.fit_science_planner_prompt(
            goal="synthetic goal",
            requirements=["R1"],
            unresolved=["R1"],
            raw_task_prompt_summary={"ordered_manifest_sha256": "a" * 64},
            declared_inputs=[],
            brain_deliverables={},
            evidence_ledger=ledger,
            requested_evidence_refs=list(requested or []),
            logical_attempt_id=LOGICAL,
            cycle=1,
        )

    def test_fit_drops_optional_expansions_until_exact_payload_fits(self):
        ledger = EvidenceLedger()
        ledger.add_record({"kind": "A", "stdout": "x" * 6000})
        ledger.add_record({"kind": "B", "stdout": "y" * 6000})

        def count(payload):
            prompt = payload["messages"][1]["content"]
            return 13000 if '"expanded":[]' not in prompt else 9000

        with patch.object(planner, "count_input_tokens", side_effect=count):
            prompt, receipt = self._fit(ledger)
        self.assertEqual(receipt["included_evidence_refs"], [])
        self.assertGreaterEqual(len(receipt["omitted_evidence_refs"]), 1)
        self.assertLessEqual(
            receipt["required_context_tokens"], planner.SERVER_CONTEXT_TOKENS
        )
        self.assertIn('"expanded":[]', prompt)

    def test_fit_payload_hash_equals_exact_payload_that_would_be_sent(self):
        ledger = EvidenceLedger()
        ledger.add_record({"kind": "OBS", "stdout": "short"})
        with patch.object(planner, "count_input_tokens", return_value=1000):
            prompt, receipt = self._fit(ledger)
        payload, _ = planner.build_request_payload(
            prompt, logical_attempt_id=LOGICAL, cycle=1
        )
        actual = hashlib.sha256(planner._payload_bytes(payload)).hexdigest()
        self.assertEqual(receipt["payload_sha256"], actual)

    def test_fixed_context_overflow_fails_closed(self):
        ledger = EvidenceLedger()
        with patch.object(
            planner,
            "count_input_tokens",
            return_value=planner.SERVER_CONTEXT_TOKENS,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "FIXED_CONTEXT_ENVELOPE_EXCEEDED"
            ):
                self._fit(ledger)

    def test_prompt_uses_refs_not_large_evidence_bytes(self):
        ledger = EvidenceLedger()
        secret = "UNIQUE-LONG-EVIDENCE-" + ("q" * 6000)
        record_ref = ledger.add_record({"kind": "OBS", "stdout": secret})
        with patch.object(planner, "count_input_tokens", return_value=1000):
            prompt, receipt = self._fit(ledger)
        self.assertIn(record_ref, prompt)
        self.assertNotIn(secret, prompt)
        self.assertIn("$evidence_text_ref", prompt)
        self.assertTrue(receipt["included_evidence_refs"])

    def test_requested_chunk_is_retrievable_losslessly_into_active_context(self):
        ledger = EvidenceLedger()
        secret = "CHUNK-DATA-" + ("z" * 5000)
        record_ref = ledger.add_record({"kind": "OBS", "stdout": secret})
        record = ledger.get(record_ref)
        text_manifest_ref = record["value"]["stdout"]["$evidence_text_ref"]
        manifest = ledger.get(text_manifest_ref)
        chunk_ref = manifest["chunk_refs"][0]
        chunk_text = ledger.get(chunk_ref)["text"]
        with patch.object(planner, "count_input_tokens", return_value=1000):
            prompt, receipt = self._fit(ledger, [chunk_ref])
        self.assertEqual(receipt["included_evidence_refs"][0], chunk_ref)
        self.assertIn(chunk_text, prompt)

    def test_planner_schema_bounds_non_effectful_evidence_requests(self):
        props = planner.TOOL["function"]["parameters"]["properties"]
        schema = props["evidence_requests"]
        self.assertEqual(schema["maxItems"], 4)
        self.assertEqual(schema["items"]["minLength"], 71)
        self.assertEqual(schema["items"]["maxLength"], 71)

    def test_legacy_lossy_observation_tail_is_absent(self):
        source = inspect.getsource(agent)
        self.assertNotIn("observations[-8:]", source)
        self.assertNotIn("[:30000]", source)

    def test_evidence_request_cycle_has_no_environment_effect(self):
        seed_observation = {"kind": "SEED", "stdout": "evidence"}
        expected_ref = EvidenceLedger().add_record(seed_observation)
        calls = []

        def fake_plan(prompt, *, logical_attempt_id, cycle, timeout_s):
            calls.append((cycle, prompt))
            payload, _ = planner.build_request_payload(
                prompt,
                logical_attempt_id=logical_attempt_id,
                cycle=cycle,
            )
            payload_sha = hashlib.sha256(planner._payload_bytes(payload)).hexdigest()
            proposal = (
                {
                    "material_requirements": ["R1"],
                    "evidence_requests": [expected_ref],
                }
                if cycle == 0
                else {
                    "material_requirements": ["IGNORED_LATER_DECLARATION"],
                }
            )
            return {
                "text": json.dumps(proposal),
                "payload_sha256": payload_sha,
                "model": planner.MODEL,
            }

        class Environment:
            async def exec(self, *args, **kwargs):
                raise AssertionError("evidence retrieval must not execute environment commands")

        with patch.object(
            agent,
            "_snapshot_declared_inputs",
            new=AsyncMock(return_value=[seed_observation]),
        ), patch.object(
            planner, "count_input_tokens", return_value=1000
        ), patch.object(
            planner, "plan", side_effect=fake_plan
        ):
            result = asyncio.run(
                agent.run_science_goal(
                    "Analyze this synthetic evidence.",
                    Environment(),
                    max_cycles=2,
                )
            )

        retrieval = [
            row for row in result["trace"]
            if row.get("kind") == "BRAIN_EVIDENCE_RETRIEVAL_REQUEST"
        ]
        self.assertEqual(len(retrieval), 1)
        self.assertEqual(retrieval[0]["requested_refs"], [expected_ref])
        self.assertIs(retrieval[0]["task_environment_effect"], False)
        self.assertEqual([c[0] for c in calls], [0, 1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
