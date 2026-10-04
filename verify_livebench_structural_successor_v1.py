#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SUB = ROOT / "subject" / "livebench_structural_successor_v1"
EXPECTED = {
    "canonical/runtime/root2_livebench_if_structural_successor_adapter_v1.py":
        "e07509aaba6cc062188eae71e83aba29547e1775",
    "canonical/runtime/instruction_constraint_compiler_v1.py":
        "a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
}


def git_blob_sha(path: pathlib.Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def verify_exact_bytes() -> None:
    for rel, expected in EXPECTED.items():
        observed = git_blob_sha(SUB / rel)
        if observed != expected:
            raise AssertionError(f"BLOB_DRIFT:{rel}:{observed}:{expected}")


def req(text: str) -> dict:
    return {
        "benchmark_id": "LIVEBENCH_IF_2026_06_25",
        "task_id": "synthetic",
        "task_payload": text,
        "allowed_tools": [],
    }


def main() -> int:
    verify_exact_bytes()
    sys.path.insert(0, str(SUB))
    mod = importlib.import_module(
        "canonical.runtime.root2_livebench_if_structural_successor_adapter_v1"
    )

    direct_calls = 0

    def forbidden(*args, **kwargs):
        nonlocal direct_calls
        direct_calls += 1
        raise AssertionError("GENERAL_RUNTIME_CALLED_FROM_DIRECT_ROUTE")

    mod.astra_runtime.run_goal = forbidden

    exact = mod.infer(req('Reply with exactly "ALPHA".'))
    assert exact["answer"] == "ALPHA"
    assert exact["status"] == "PASS__PRECOMPILED_STRUCTURAL_SUCCESSOR_RESPONSE"
    assert exact["cognition_dependency_class"] == "MODEL_INDEPENDENT"
    assert exact["model_dependency_count"] == 0
    assert exact["tool_trace"][0]["post_prompt_acquisition"] is False
    assert exact["tool_trace"][0]["external_tools_used"] is False
    assert exact["tool_trace"][0]["model_used"] is False

    structural = mod.infer(
        req("Use exactly 5 words and include exactly 2 numbers.")
    )
    words = structural["answer"].split()
    assert len(words) == 5
    assert sum(x.isdigit() for x in words) == 2
    assert structural["status"] == "PASS__PRECOMPILED_STRUCTURAL_SUCCESSOR_RESPONSE"
    assert structural["tool_trace"][0]["semantic_seed_required_by_general_use"] is True
    assert direct_calls == 0

    seen = {}

    def fake_run_goal(step, mission):
        seen["step"] = step
        seen["mission"] = mission
        return {
            "stdout": "owned local fallback",
            "trace": [{"adapter": "verifier_stub"}],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
        }

    mod.astra_runtime.run_goal = fake_run_goal
    fallback = mod.infer(req("Explain photosynthesis."))
    assert fallback["answer"] == "owned local fallback"
    assert fallback["status"] == "PASS__MODEL_INDEPENDENT_BRAIN_FALLBACK_RESPONSE"
    assert seen["step"]["allow_optional_model_planner"] is False
    assert seen["step"]["max_controller_actions"] == 16
    assert seen["step"]["max_cycles"] == 6

    bad = req('Reply with exactly "ALPHA".')
    bad["allowed_tools"] = ["web"]
    try:
        mod.infer(bad)
    except mod.LiveBenchStructuralSuccessorBlocked as exc:
        assert "EXTERNAL_TOOLS_FORBIDDEN" in str(exc)
    else:
        raise AssertionError("EXTERNAL_TOOL_ROUTE_NOT_BLOCKED")

    bad = req('Reply with exactly "ALPHA".')
    bad["benchmark_id"] = "OTHER"
    try:
        mod.infer(bad)
    except mod.LiveBenchStructuralSuccessorBlocked as exc:
        assert "BENCHMARK_ID_MISMATCH" in str(exc)
    else:
        raise AssertionError("BENCHMARK_ID_DRIFT_NOT_BLOCKED")

    result = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_STRUCTURAL_SUCCESSOR_PUBLIC_RUNNER_VERIFICATION_V1",
        "exact_subject_blobs": EXPECTED,
        "synthetic_direct_cases": 2,
        "fallback_contract_cases": 1,
        "fail_closed_cases": 2,
        "direct_general_runtime_calls": direct_calls,
        "direct_post_prompt_acquisition": False,
        "direct_external_tools_used": False,
        "direct_model_dependency_count": 0,
        "network_used_by_verifier": False,
        "terminal_cases_consumed": 0,
        "case_73_plus_exposed": False,
        "acceptance_credit_delta": 0,
        "conclusion": "PASS",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
