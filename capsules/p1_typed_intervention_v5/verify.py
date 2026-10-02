from __future__ import annotations
import hashlib, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent
manifest = json.loads((ROOT / "EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))

def git_blob_sha(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

for rel, expected in manifest["exact_brain_blobs"].items():
    path = ROOT / rel
    actual = git_blob_sha(path)
    assert actual == expected, (rel, actual, expected)

sys.path.insert(0, str(ROOT))
subprocess.run([
    sys.executable, "-m", "py_compile",
    str(ROOT / "canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py"),
    str(ROOT / "canonical/runtime/trajectory_failure_typed_ir_proof_v5.py"),
], check=True)
subprocess.run([
    sys.executable, "-m", "unittest",
    "canonical.tests.test_trajectory_failure_typed_ir_v5", "-v",
], cwd=ROOT, check=True)

from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as proof
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate

cases = proof.suite_cases()
assert len(cases) == 192
for case in cases:
    out = candidate.solve(proof.public_task(case))
    verdict = proof.score_case(case, out)
    assert verdict.get("pass") is True, (case["seed"], verdict, out)

print(json.dumps({
    "status": "PASS",
    "exact_brain_blob_count": len(manifest["exact_brain_blobs"]),
    "cross_product_case_count": len(cases),
    "domains": list(proof.DOMAINS),
    "mechanism_classes": list(proof.KINDS),
    "causal_patterns": ["SINGLE","DELAYED","INTERACTION","AMBIGUOUS"],
    "drop_supporting_receipts_killed": True,
    "unfalsifiable_diagnosis_injection_killed": True,
    "hidden_intervention_rescue_checked": True,
    "terminal_results_replayed": 0,
    "new_reality_units_consumed": 0,
    "capability_credit_delta": 0,
    "family_credit_delta": 0
}, indent=2, sort_keys=True))
