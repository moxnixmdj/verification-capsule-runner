#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "mm_sparse_adapter_v1"

EXPECTED = {
    "canonical/governance/MYSTERYMECHANISM_SPARSE_SYMBOLIC_ADAPTER_PREEXPOSURE_V1.json": "5f26616e883d9de49b65f918d3c9e926cbbb24cf",
    "canonical/runtime/mysterymechanism_sparse_symbolic_adapter_v1.py": "ca70007a843e98489a24addac61a8ce16c22daa8",
    "canonical/tests/test_mysterymechanism_sparse_symbolic_adapter_v1.py": "376ba3adb47db1592545d1625c1516beca2545ef",
    "canonical/runtime/h100_zero_learned_mechanism_synthesizer_v1.py": "fa77c6a0f4edf214c4237cf1e204b640261622fe",
}

def blob_sha(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def main() -> int:
    got = {p: blob_sha(SUBJECT / p) for p in EXPECTED}
    assert got == EXPECTED, (got, EXPECTED)

    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(SUBJECT)
    test = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "canonical.tests.test_mysterymechanism_sparse_symbolic_adapter_v1"],
        cwd=SUBJECT, env=env, text=True, capture_output=True,
    )
    print(test.stdout)
    print(test.stderr)
    assert test.returncode == 0, "BRAIN_AUTHORED_TESTS_FAILED"

    sys.path.insert(0, str(SUBJECT))
    from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v1 as mm

    fresh = {}

    rows = [{"x": x, "out": 1.75*x + 2.25*(x/(1+abs(x)))}
            for x in (-5.0,-2.25,-0.6,0.2,0.9,2.8,6.0)]
    d = mm.sparse_discover(rows, target="out", max_depth=2)
    assert d["status"] == "SPARSE_CANDIDATES_FOUND", d
    assert d["best_candidate"]["loo_nrmse"] < 1e-7, d["best_candidate"]
    fresh["saturation_fresh"] = {
        "pass": True,
        "loo_nrmse": d["best_candidate"]["loo_nrmse"],
        "all_nrmse": d["best_candidate"]["all_nrmse"],
    }

    rows = [{"x": x, "out": 2.2*(abs(x)**(2/3))+0.7}
            for x in (-8.0,-3.0,-0.5,0.3,1.2,4.0,9.0)]
    d = mm.sparse_discover(rows, target="out", max_depth=1)
    assert d["best_candidate"]["loo_nrmse"] < 1e-7, d["best_candidate"]
    fresh["rational_power_fresh"] = {
        "pass": True,
        "loo_nrmse": d["best_candidate"]["loo_nrmse"],
        "all_nrmse": d["best_candidate"]["all_nrmse"],
    }

    points = [(1.0,0.2),(2.0,0.5),(4.0,1.0),(7.0,2.0),(3.0,4.0),(8.0,0.8),(5.0,3.0)]
    rows = [{"x":x,"z":z,"out":1.1+3.7*x/(1+abs(z))} for x,z in points]
    d = mm.sparse_discover(rows, target="out", max_depth=1)
    assert d["best_candidate"]["loo_nrmse"] < 1e-7, d["best_candidate"]
    fresh["ratio_correction_fresh"] = {
        "pass": True,
        "loo_nrmse": d["best_candidate"]["loo_nrmse"],
        "all_nrmse": d["best_candidate"]["all_nrmse"],
    }

    plan = mm.plan_experiments({"a":[0.05,0.70],"b":[0.05,30.0]})
    assert plan["active_budget"] == 5
    assert len(plan["initial_experiments"]) == 4
    assert plan["reserved_count"] == 1
    for point in plan["initial_experiments"] + [plan["reserved_final_experiment"]]:
        assert 0.05 <= point["a"] <= 0.70
        assert 0.05 <= point["b"] <= 30.0

    src = (SUBJECT / "canonical/runtime/mysterymechanism_sparse_symbolic_adapter_v1.py").read_text()
    assert "eval(" not in src
    assert "exec(" not in src
    assert "subprocess" not in src
    assert "requests" not in src
    assert "openai" not in src.lower()
    assert "anthropic" not in src.lower()

    receipt = {
        "schema": "PROJECT_BRAIN_MYSTERYMECHANISM_SPARSE_SYMBOLIC_ADAPTER_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__CONTENT_BOUND_SPARSE_5_TO_7_ROW_ACTIVE_SYMBOLIC_ADAPTER__FRESH_MOTIFS_PASS__ZERO_CREDIT",
        "subject_blobs": got,
        "brain_authored_tests": "PASS",\n        "finite_probe_nonidentifiability": theorem["status"],
        "fresh_independent_challenges": fresh,
        "public_contract_shape": {
            "two_dimensional_active_budget": 5,
            "initial_experiments": 4,
            "reserved_adaptive_experiment": 1,
            "all_probes_in_bounds": True,
        },
        "boundary": {
            "private_mysterymechanism_cases_used": 0,
            "private_score_claimed": False,
            "dynamic_eval": False,
            "external_learned_capability_provider": False,
            "persistent_learned_bytes": 0,
        },
        "accounting": {
            "incremental_spend_usd": 0,
            "terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }
    (ROOT / "mm_sparse_adapter_v1_verification.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
