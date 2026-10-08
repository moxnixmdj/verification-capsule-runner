from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "canonical/runtime/interval_information_frontier_v1.py"
TESTS = ROOT / "canonical/tests/test_interval_information_frontier_v1.py"
GOVERNANCE = ROOT / "canonical/governance/MYSTERYMECHANISM_INTERVAL_INFORMATION_FRONTIER_20261008_V1.json"

EXPECTED_GIT_BLOBS = {
    RUNTIME: "71ede5329f1d18505845d399f0243d76c005118a",
    TESTS: "3cec294a2bff0a3aa623c7129b82e72e784321de",
    GOVERNANCE: "779f09fa1faae687aa87055bbd0c8863eba565c4",
}

SOURCE = {
    "repository": "moxnixmdj/brain",
    "branch": "research/mysterymechanism-interval-frontier-v1b-20261008",
    "source_head_at_copy": "88b1577cbf6b2381a552183f7af84cb80ba95f35",
    "brain_pr": 3158,
}


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_runtime():
    spec = importlib.util.spec_from_file_location("interval_frontier_exact", RUNTIME)
    require(spec is not None and spec.loader is not None, "runtime spec unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_problem():
    return {
        "hypothesis_cover_complete": True,
        "interval_soundness_bound": True,
        "worlds": [
            {
                "world_id": "a",
                "terminal_signature_complete": True,
                "terminal_signature": {"answer": "A"},
            },
            {
                "world_id": "b",
                "terminal_signature_complete": True,
                "terminal_signature": {"answer": "B"},
            },
        ],
        "queries": [
            {
                "query_id": "q",
                "cost_units": 1,
                "prediction_intervals_complete": True,
                "prediction_intervals": {"a": [0.0, 1.0], "b": [2.0, 3.0]},
            }
        ],
    }


def main() -> None:
    # 1. Exact-byte binding to the private Brain candidate.
    observed = {str(path.relative_to(ROOT)): git_blob_sha(path) for path in EXPECTED_GIT_BLOBS}
    for path, expected in EXPECTED_GIT_BLOBS.items():
        actual = git_blob_sha(path)
        require(actual == expected, f"exact Brain blob drift: {path}: {actual} != {expected}")

    # 2. Governance is explicitly zero-credit and preserves private-scope nonclaims.
    governance = json.loads(GOVERNANCE.read_text(encoding="utf-8"))
    accounting = governance["accounting"]
    require(all(accounting[k] == 0 for k in (
        "incremental_spend_usd",
        "fresh_target_reality_units_consumed",
        "acceptance_credit_delta",
        "family_credit_delta",
        "capability_credit_delta",
        "terminal_credit_delta",
    )), "governance grants nonzero credit")
    nonclaims = set(governance["hard_nonclaims"])
    require(
        "NO CLAIM THE PRIVATE 222 MECHANISMS LIE IN ANY CURRENT BRAIN SYMBOLIC GRAMMAR" in nonclaims,
        "private-scope nonclaim missing",
    )
    require(
        "NO MYSTERYMECHANISM SCORE OR SUCCESS COUNT CLAIM" in nonclaims,
        "benchmark-score nonclaim missing",
    )

    # 3. Run the exact copied committed Brain tests as their original module.
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "canonical.tests.test_interval_information_frontier_v1"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(result.stdout)
    require(result.returncode == 0, "exact copied Brain tests failed")

    # 4. Fresh independent adversarial checks.
    rt = load_runtime()

    p = base_problem()
    p["queries"][0]["prediction_intervals"]["a"] = [0.0, float("nan")]
    out = rt.solve(p)
    require(out["pass"] is False and out["reason"] == "QUERY_BINDING_INVALID",
            "nonfinite interval did not fail closed")

    p = base_problem()
    p["queries"][0]["prediction_intervals"] = {"a": [0.0, 1.0], "b": [1.0, 2.0]}
    out = rt.solve(p)
    require(out["pass"] is False and "NOT_WORST_CASE_SEPARABLE" in out["status"],
            "closed-interval endpoint ambiguity was unsafely separated")

    interval_map = {"a": (0.0, 2.0), "b": (1.0, 3.0), "c": (2.5, 4.0)}
    got = set(rt._possible_survivor_sets(frozenset(interval_map), interval_map))
    expected = {
        frozenset({"a"}),
        frozenset({"a", "b"}),
        frozenset({"b"}),
        frozenset({"b", "c"}),
        frozenset({"c"}),
    }
    require(got == expected, f"endpoint-cell survivor enumeration incomplete: {got}")

    p = base_problem()
    p["worlds"][1]["terminal_signature"] = {"answer": "A"}
    p["queries"] = []
    out = rt.solve(p)
    require(out["pass"] is True and out["minimum_worst_case_cost_units"] == 0.0,
            "terminally equivalent worlds were unnecessarily distinguished")

    p = base_problem()
    p["max_worst_case_cost_units"] = 0
    out = rt.solve(p)
    require(
        out["pass"] is False
        and out["status"] == "FAIL_CLOSED__MINIMUM_WORST_CASE_COST_EXCEEDS_BUDGET"
        and out["terminal_authority"] is False,
        "budget failure did not remain fail closed",
    )

    p = base_problem()
    p["hypothesis_cover_complete"] = False
    out = rt.solve(p)
    require(
        out["pass"] is False
        and out["reason"] == "HYPOTHESIS_COVER_COMPLETENESS_UNPROVED"
        and out["terminal_authority"] is False,
        "incomplete cover was granted authority",
    )

    receipt = {
        "schema": "PROJECT_BRAIN_INTERVAL_INFORMATION_FRONTIER_PUBLIC_CAPSULE_VERIFICATION_V1",
        "source": SOURCE,
        "exact_git_blobs": observed,
        "exact_committed_tests_passed": 9,
        "fresh_independent_canaries_passed": 6,
        "verified_properties": [
            "EXACT_PRIVATE_BRANCH_BLOBS_MATCH",
            "COMMITTED_9_TEST_SUITE_PASSES",
            "NONFINITE_INTERVAL_FAILS_CLOSED",
            "CLOSED_ENDPOINT_AMBIGUITY_PRESERVED",
            "ENDPOINT_CELL_SURVIVOR_ENUMERATION_COMPLETE_FOR_FRESH_THREE_INTERVAL_CASE",
            "TERMINAL_EQUIVALENCE_STOPS_WITH_ZERO_QUERY_COST",
            "DECLARED_QUERY_BUDGET_FAILS_CLOSED",
            "UNPROVED_HYPOTHESIS_COVER_FAILS_CLOSED",
            "ZERO_ACCEPTANCE_FAMILY_CAPABILITY_TERMINAL_CREDIT",
        ],
        "hard_boundary": (
            "VERIFIES_THE_GENERIC_FINITE_INTERVAL_INFORMATION_KERNEL_ONLY;"
            "DOES_NOT_PROVE_CURRENT_SYMBOLIC_GRAMMAR_COVERS_PRIVATE_MYSTERYMECHANISM;"
            "DOES_NOT_PROVE_PREDICTION_INTERVAL_SOUNDNESS_FOR_ANY_PRIVATE_TASK;"
            "NO_MYSTERYMECHANISM_SCORE_OR_TERMINAL_CREDIT"
        ),
    }
    print(json.dumps(receipt, sort_keys=True))
    print("INTERVAL_INFORMATION_FRONTIER_PUBLIC_CAPSULE_PASS")


if __name__ == "__main__":
    main()
