from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from canonical.runtime import harbor_science_agent_v2 as agent
from canonical.runtime import harbor_science_planner_v2 as planner
import rank15_prestart_token_guard_v2 as prestart


LOGICAL_ID = "a" * 64


class Response:
    def __init__(self, obj: dict, status: int = 200):
        self._body = json.dumps(obj).encode("utf-8")
        self.status = status

    def read(self, n: int = -1):
        return self._body if n < 0 else self._body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def tool_response() -> dict:
    return {
        "model": planner.MODEL,
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {
                "role": "assistant",
                "tool_calls": [{
                    "type": "function",
                    "function": {
                        "name": planner.TOOL_NAME,
                        "arguments": json.dumps({
                            "material_requirements": ["R1"],
                            "candidates": [{
                                "action_id": "A1",
                                "covers": ["R1"],
                                "command": "echo x",
                                "verify_command": "test true",
                            }],
                        }),
                    },
                }],
            },
        }],
    }


class Rank15V2RuntimeTests(unittest.TestCase):
    def test_same_semantic_request_produces_same_seeded_wire_payload(self):
        a, ma = planner.build_request_payload(
            "synthetic", logical_attempt_id=LOGICAL_ID, cycle=3
        )
        b, mb = planner.build_request_payload(
            "synthetic", logical_attempt_id=LOGICAL_ID, cycle=3
        )
        self.assertEqual(a, b)
        self.assertEqual(planner._payload_bytes(a), planner._payload_bytes(b))
        self.assertEqual(ma, mb)
        self.assertEqual(a["seed"], ma["seed"])

    def test_cycle_changes_request_identity_without_carrier_identity(self):
        p0, m0 = planner.build_request_payload(
            "synthetic", logical_attempt_id=LOGICAL_ID, cycle=0
        )
        p1, m1 = planner.build_request_payload(
            "synthetic", logical_attempt_id=LOGICAL_ID, cycle=1
        )
        self.assertNotEqual(m0["request_identity_sha256"], m1["request_identity_sha256"])
        self.assertEqual(m0["logical_attempt_id"], LOGICAL_ID)
        self.assertEqual(m1["logical_attempt_id"], LOGICAL_ID)
        self.assertNotIn("GITHUB_RUN_ID", planner._payload_bytes(p0).decode())
        self.assertNotIn("GITHUB_RUN_ID", planner._payload_bytes(p1).decode())

    def test_context_overflow_never_reaches_inference_endpoint(self):
        called = []

        def forbidden(*args, **kwargs):
            called.append((args, kwargs))
            raise AssertionError("inference endpoint must not be called")

        with patch.object(
            planner, "count_input_tokens",
            return_value=planner.SERVER_CONTEXT_TOKENS
            - planner.MAX_TOOL_COMPLETION_TOKENS + 1,
        ), patch.object(planner.urllib.request, "urlopen", side_effect=forbidden):
            with self.assertRaisesRegex(
                planner.SciencePlannerError, "CONTEXT_ENVELOPE_EXCEEDED"
            ):
                planner.plan(
                    "synthetic",
                    logical_attempt_id=LOGICAL_ID,
                    cycle=0,
                    timeout_s=300,
                )
        self.assertEqual(called, [])

    def test_exact_context_boundary_is_admitted(self):
        seen = []

        def fake(req, timeout=0):
            seen.append(req.full_url)
            return Response(tool_response())

        with patch.object(
            planner, "count_input_tokens",
            return_value=planner.SERVER_CONTEXT_TOKENS
            - planner.MAX_TOOL_COMPLETION_TOKENS,
        ), patch.object(planner.urllib.request, "urlopen", side_effect=fake):
            out = planner.plan(
                "synthetic",
                logical_attempt_id=LOGICAL_ID,
                cycle=0,
                timeout_s=300,
            )
        self.assertEqual(seen, [planner.ENDPOINT])
        self.assertEqual(out["context_headroom_tokens"], 0)
        self.assertEqual(out["required_context_tokens"], planner.SERVER_CONTEXT_TOKENS)

    def test_action_timeout_authority_matches_transport_ceiling(self):
        self.assertEqual(agent.MAX_ACTION_TIMEOUT_S, 3600)
        schema = (
            planner.TOOL["function"]["parameters"]["properties"]["candidates"]
            ["items"]["properties"]["timeout_sec"]
        )
        self.assertEqual(schema["maximum"], 3600)
        bad = [{
            "action_id": "A1",
            "covers": ["R1"],
            "timeout_sec": 3601,
            "command": "echo x",
            "verify_command": "test true",
        }]
        with self.assertRaisesRegex(RuntimeError, "ACTION_TIMEOUT_INVALID"):
            agent._candidate_rows(bad, {"R1"})

    def test_prompt_builder_is_deterministic(self):
        kwargs = dict(
            goal="synthetic goal",
            requirements=["R1"],
            unresolved=["R1"],
            raw_task_prompt_summary={"ordered_manifest_sha256": "b" * 64},
            declared_inputs=[],
            brain_deliverables={},
            observations=[{"kind": "OBS", "value": 1}],
        )
        self.assertEqual(
            agent.build_science_planner_prompt(**kwargs),
            agent.build_science_planner_prompt(**kwargs),
        )

    def test_prestart_calls_runtime_prompt_builder(self):
        sentinel = "CANONICAL_RUNTIME_PROMPT_SENTINEL"
        with patch.object(
            prestart.agent,
            "_compile_lossless_task_scope",
            return_value=(
                {"acceptance_contract": {"required_obligation_ids": ["R"]}},
                {"obligations": [{"obligation_id": "R"}]},
                [{"obligation_id": "R"}],
            ),
        ), patch.object(
            prestart.agent,
            "_planner_raw_task_manifest_summary",
            return_value={"ordered_manifest_sha256": "c" * 64},
        ), patch.object(
            prestart.agent,
            "_brain_mandated_deliverables",
            return_value={},
        ), patch.object(
            prestart.agent,
            "_declared_task_paths",
            return_value=([], []),
        ), patch.object(
            prestart.agent,
            "build_science_planner_prompt",
            return_value=sentinel,
        ) as shared:
            prompt, *_rest = prestart._first_cycle_prompt("synthetic goal")
        self.assertEqual(prompt, sentinel)
        shared.assert_called_once()

    def test_logical_attempt_identity_is_goal_bound_and_carrier_independent(self):
        a = agent.logical_attempt_id_for_goal(" same goal ")
        b = agent.logical_attempt_id_for_goal("same goal")
        c = agent.logical_attempt_id_for_goal("different goal")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(a), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
