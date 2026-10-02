from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
manifest = json.loads((ROOT / "EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))


def git_blob_sha(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


for rel, expected in manifest["exact_brain_blobs"].items():
    actual = git_blob_sha(ROOT / rel)
    assert actual == expected, (rel, actual, expected)

sys.path.insert(0, str(ROOT))

subprocess.run(
    [
        sys.executable,
        "-m",
        "unittest",
        "canonical.tests.test_p1_v5_intervention_replay_semantic_audit_v1",
        "-v",
    ],
    cwd=ROOT,
    check=True,
)

from canonical.runtime import p1_v5_intervention_replay_semantic_audit_v1 as audit

out = audit.audit()
assert out["status"].startswith("PASS__V5_INTERVENTION_REPLAY_CLAIM_FALSIFIED"), out
assert out["all_counterexamples_reproduced"] is True, out
assert out["counterexample_count"] == 4, out
assert out["v5_heterogeneous_intervention_rescue_semantics_valid"] is False, out
assert out["p1_scope_quarantine_clearable_from_v5"] is False, out
assert out["terminal_results_replayed"] == 0, out
assert out["new_reality_units_consumed"] == 0, out
assert out["capability_credit_delta"] == 0, out
assert out["family_credit_delta"] == 0, out
assert out["execution_authority"] is False, out
assert out["promotion_authority"] is False, out

print(json.dumps({
    "status": "PASS__INDEPENDENT_REPRODUCTION_OF_P1_V5_INTERVENTION_REPLAY_FALSIFICATION",
    "brain_ref": manifest["brain_ref"],
    "exact_brain_blob_count": len(manifest["exact_brain_blobs"]),
    "counterexample_count": out["counterexample_count"],
    "all_counterexamples_reproduced": out["all_counterexamples_reproduced"],
    "v5_heterogeneous_intervention_rescue_semantics_valid": out["v5_heterogeneous_intervention_rescue_semantics_valid"],
    "p1_scope_quarantine_clearable_from_v5": out["p1_scope_quarantine_clearable_from_v5"],
    "credit_delta": 0,
}, indent=2, sort_keys=True))
