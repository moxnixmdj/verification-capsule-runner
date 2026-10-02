from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    "canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json": "1da223b8133e83d3ba1b238012593b39dcae91f9",
    "canonical/runtime/trajectory_failure_typed_ir_candidate_v4.py": "0c386e6b78a8e97e9c1944e63600047bc4e2849b",
    "canonical/runtime/trajectory_failure_typed_ir_proof_v4.py": "6e1dfaa6b63fc629d55d07b2361bf625f11a5ce3",
    "canonical/runtime/p1_composite_proof_role_verifier_v1.py": "fdede791432ce24244885c3f11f4de40a82b493e",
    "canonical/tests/test_p1_composite_proof_role_verifier_v1.py": "762cad874556353a3862525c94e29376995bd3b6",
}

def blob(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

for rel, expected in EXPECTED.items():
    got = blob(ROOT / rel)
    assert got == expected, (rel, got, expected)

recon = json.loads((ROOT / "canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json").read_text())
v4_mut = recon["mutation_roles"]["V4_TYPED_CROSS_DOMAIN_PREFLIGHT"]
assert "DROP_PROVENANCE_OR_DEPENDENCY_EDGE" in v4_mut, v4_mut

candidate = load_module("candidate_v4", "canonical/runtime/trajectory_failure_typed_ir_candidate_v4.py")
proof = load_module("proof_v4", "canonical/runtime/trajectory_failure_typed_ir_proof_v4.py")

case = proof.generate_case(41001, pattern="SINGLE", domain="RESEARCH", kind="PROVENANCE")
public = copy.deepcopy(proof.public_task(case))
erased = 0
for row in public["task"]["trajectory"]:
    for check in row["checks"]:
        if check.get("pass") is False:
            check["evidence"] = []
            erased += 1

answer = candidate.solve(public)
verdict = proof.score_case(case, answer)
counterexample_holds = (
    erased > 0
    and answer.get("supporting_receipts") == []
    and verdict.get("pass") is True
)
assert counterexample_holds, {
    "erased": erased,
    "answer": answer,
    "verdict": verdict,
}

verifier_src = (ROOT / "canonical/runtime/p1_composite_proof_role_verifier_v1.py").read_text()
assert 'V4_DROP_PROVENANCE_MUTATION_SURVIVES_SCORER' in verifier_src
assert 'if v4_provenance_counterexample["counterexample_holds"]:' in verifier_src
assert '"quarantine_lift_eligible": not unique' in verifier_src

print(json.dumps({
    "status": "INDEPENDENT_PASS__CORRECTED_P1_ROLE_TABLE_STILL_FALSIFIED_BY_V4_PROVENANCE_COUNTEREXAMPLE",
    "exact_blob_count": len(EXPECTED),
    "assigned_mutation": "DROP_PROVENANCE_OR_DEPENDENCY_EDGE",
    "assigned_role": "V4_TYPED_CROSS_DOMAIN_PREFLIGHT",
    "failed_check_receipt_lists_erased": erased,
    "candidate_supporting_receipts": answer.get("supporting_receipts"),
    "scorer_pass_after_mutation": verdict.get("pass") is True,
    "counterexample_holds": counterexample_holds,
    "brain_verifier_fail_closed_binding_present": True,
    "quarantine_lift_eligible": False,
    "terminal_results_replayed": 0,
    "new_reality_units_consumed": 0,
    "capability_credit_delta": 0,
    "family_credit_delta": 0,
}, indent=2, sort_keys=True))
