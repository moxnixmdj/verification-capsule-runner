from __future__ import annotations

import importlib.util
import json
from hashlib import sha1
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "runtime.py"
GOVERNANCE = ROOT / "governance.json"
SOURCE_TESTS = ROOT / "source_tests.py"

EXPECTED = {
    "runtime.py": "1282ed322fcb7b1b1889000778966da3572020db",
    "governance.json": "2546e8d75ee829cf8baf36558c0dbac759527a1a",
    "source_tests.py": "044235b7c12b8e077f5a839626fc036a4591f0d7",
}

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load_runtime():
    spec = importlib.util.spec_from_file_location("terminal_progress_delta_gate_v1", RUNTIME)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

def main() -> None:
    observed = {
        "runtime.py": git_blob_sha(RUNTIME),
        "governance.json": git_blob_sha(GOVERNANCE),
        "source_tests.py": git_blob_sha(SOURCE_TESTS),
    }
    assert observed == EXPECTED, (observed, EXPECTED)

    gov = json.loads(GOVERNANCE.read_text())
    assert gov["schema"] == "PROJECT_BRAIN_TERMINAL_PROGRESS_DELTA_GATE_V1"
    assert gov["independent_verification_required"] is True
    assert gov["accounting"] == {
        "incremental_spend_usd": 0,
        "new_reality_units_consumed": 0,
        "terminal_cases_consumed": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }

    m = load_runtime()
    A40 = "a" * 40

    def state(truth, interfaces, prereqs, depth, nodes):
        raw = {
            "schema": m.STATE_SCHEMA,
            "open_truth_obligations": list(truth),
            "active_causal_interfaces": list(interfaces),
            "open_prerequisites": list(prereqs),
            "max_open_causal_depth": depth,
            "open_proof_node_count": nodes,
        }
        raw["state_sha256"] = m.sha256_json(raw)
        return raw

    def receipt(before, after, targets, effect, path="canonical/verification/X.json"):
        return {
            "path": path,
            "git_blob_sha": A40,
            "before_state_sha256": before["state_sha256"],
            "after_state_sha256": after["state_sha256"],
            "target_truth_obligations_sha256": m.sha256_json(sorted(targets)),
            "effect_kind": effect,
        }

    checks = []

    def run(name, condition):
        assert condition, name
        checks.append(name)

    # Direct truth closure.
    b = state(["P1", "P2"], ["I1", "I2"], ["A", "B"], 3, 7)
    a = state(["P2"], ["I1", "I2"], ["A", "B"], 3, 7)
    t = ["P1"]
    out = m.compile_result({
        "schema": m.INPUT_SCHEMA, "kind": "PROGRESS", "before": b, "after": a,
        "target_truth_obligations": t,
        "evidence_receipts": [receipt(b, a, t, "TRUTH_CLOSURE")],
    })
    run("DIRECT_TRUTH_CLOSURE", out["status"] == "ADMIT_TERMINAL_CONTRACTING_PROGRESS" and out["counts_as_progress"] is True)

    # Each lower-order contraction class is independently admissible.
    cases = [
        ("INTERFACE_CONTRACTION", state(["P"], ["I1", "I2"], ["A"], 3, 5), state(["P"], ["I1"], ["A"], 3, 5)),
        ("DEPTH_CONTRACTION", state(["P"], ["I1"], ["A"], 3, 5), state(["P"], ["I1"], ["A"], 2, 5)),
        ("PREREQUISITE_CONTRACTION", state(["P"], ["I1"], ["A", "B"], 2, 5), state(["P"], ["I1"], ["A"], 2, 5)),
        ("PROOF_NODE_CONTRACTION", state(["P"], ["I1"], ["A"], 2, 5), state(["P"], ["I1"], ["A"], 2, 4)),
    ]
    for effect, b, a in cases:
        t = ["P"]
        out = m.compile_result({
            "schema": m.INPUT_SCHEMA, "kind": "PROGRESS", "before": b, "after": a,
            "target_truth_obligations": t,
            "evidence_receipts": [receipt(b, a, t, effect)],
        })
        run(effect, out["status"] == "ADMIT_TERMINAL_CONTRACTING_PROGRESS")

    # No contraction = no progress, even if names change.
    b = state(["P"], ["I1"], ["A"], 2, 4)
    a = state(["P"], ["I1"], ["RENAMED"], 2, 4)
    out = m.compile_result({
        "schema": m.INPUT_SCHEMA, "kind": "PROGRESS", "before": b, "after": a,
        "target_truth_obligations": ["P"], "evidence_receipts": [],
    })
    run("REPACKAGING_REJECTED", out["status"] == "REJECT_NONCONTRACTING_PROGRESS")

    # Growth is rejected as progress.
    a = state(["P"], ["I1"], ["A", "B"], 2, 5)
    out = m.compile_result({
        "schema": m.INPUT_SCHEMA, "kind": "PROGRESS", "before": b, "after": a,
        "target_truth_obligations": ["P"], "evidence_receipts": [],
    })
    run("CHAIN_GROWTH_REJECTED", out["status"] == "REJECT_NONCONTRACTING_PROGRESS")

    # Progress cannot introduce new terminal truth.
    b2 = state(["P1"], ["I1", "I2"], ["A"], 2, 4)
    a2 = state(["P1", "P2"], ["I1"], [], 1, 1)
    out = m.compile_result({
        "schema": m.INPUT_SCHEMA, "kind": "PROGRESS", "before": b2, "after": a2,
        "target_truth_obligations": ["P1"], "evidence_receipts": [],
    })
    run("NEW_TRUTH_REJECTED_AS_PROGRESS", out["status"] == "REJECT_NONCONTRACTING_PROGRESS")

    # Constructive truth repair may worsen the potential, but receives zero progress credit.
    t = ["P1"]
    cr = receipt(b2, a2, t, "TRUTH_REPAIR", "canonical/verification/COUNTERMODEL.json")
    out = m.compile_result({
        "schema": m.INPUT_SCHEMA, "kind": "TRUTH_REPAIR", "before": b2, "after": a2,
        "target_truth_obligations": t, "countermodel_receipts": [cr],
    })
    run("TRUTH_REPAIR_ZERO_PROGRESS", out["status"] == "ADMIT_TRUTH_REPAIR_NOT_PROGRESS" and out["counts_as_progress"] is False and out["recompute_required"] is True)

    # Missing receipt on an otherwise valid contraction fails closed.
    b3 = state(["P"], ["I1", "I2"], ["A"], 2, 4)
    a3 = state(["P"], ["I1"], ["A"], 2, 4)
    out = m.compile_result({
        "schema": m.INPUT_SCHEMA, "kind": "PROGRESS", "before": b3, "after": a3,
        "target_truth_obligations": ["P"], "evidence_receipts": [],
    })
    run("MISSING_RECEIPT_FAIL_CLOSED", out["status"] == "FAIL_CLOSED")

    # Unrelated content-addressed receipt cannot authorize a real contraction.
    t = ["P"]
    bad = receipt(b3, a3, t, "INTERFACE_CONTRACTION")
    bad["before_state_sha256"] = "b" * 64
    out = m.compile_result({
        "schema": m.INPUT_SCHEMA, "kind": "PROGRESS", "before": b3, "after": a3,
        "target_truth_obligations": t, "evidence_receipts": [bad],
    })
    run("UNRELATED_RECEIPT_FAIL_CLOSED", out["status"] == "FAIL_CLOSED" and "EVIDENCE_RECEIPTS_BEFORE_STATE_BINDING_MISMATCH" in out["errors"])

    # Wrong effect kind cannot authorize a contraction.
    bad = receipt(b3, a3, t, "TRUTH_CLOSURE")
    out = m.compile_result({
        "schema": m.INPUT_SCHEMA, "kind": "PROGRESS", "before": b3, "after": a3,
        "target_truth_obligations": t, "evidence_receipts": [bad],
    })
    run("WRONG_EFFECT_FAIL_CLOSED", out["status"] == "FAIL_CLOSED" and "EVIDENCE_RECEIPTS_EFFECT_KIND_MISMATCH" in out["errors"])

    # Target must be a currently open truth obligation.
    out = m.compile_result({
        "schema": m.INPUT_SCHEMA, "kind": "PROGRESS", "before": b3, "after": a3,
        "target_truth_obligations": ["NOT_OPEN"], "evidence_receipts": [],
    })
    run("TARGET_OUTSIDE_OPEN_SET_FAIL_CLOSED", out["status"] == "FAIL_CLOSED")

    # State-content binding is fail closed.
    tampered = dict(b3)
    tampered["state_sha256"] = "c" * 64
    out = m.compile_result({
        "schema": m.INPUT_SCHEMA, "kind": "PROGRESS", "before": tampered, "after": a3,
        "target_truth_obligations": ["P"], "evidence_receipts": [],
    })
    run("STATE_HASH_TAMPER_FAIL_CLOSED", out["status"] == "FAIL_CLOSED")

    print(json.dumps({
        "schema": "PROJECT_BRAIN_TERMINAL_PROGRESS_DELTA_GATE_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__EXACT_BRAIN_BLOBS__TERMINAL_CONTRACTION_AND_TRUTH_REPAIR_SEPARATION_VERIFIED__ZERO_CREDIT",
        "exact_source_git_blob_shas": EXPECTED,
        "checks": checks,
        "check_count": len(checks),
        "accounting": {
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
