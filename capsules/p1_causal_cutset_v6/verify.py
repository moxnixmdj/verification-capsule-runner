from __future__ import annotations
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/runtime/p1_causal_cutset_v6.py": "1e02dedeafd10388b188188e40df3537b7788c4b",
    "canonical/runtime/p1_causal_cutset_v6_proof.py": "000ba210a24854bcdedf828999866f897a949358",
    "canonical/tests/test_p1_causal_cutset_v6.py": "a467a455c339b057649c3bcd7182d77778139b6d",
    "canonical/governance/P1_EXECUTABLE_CAUSAL_CUTSET_V6.json": "9099821f0d61a61ca55d0ac4015594f1737f53f7",
    "canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py": "2a8613ddac7402c7e6d2f349f9d3c32d3fb95e1d",
}

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()

for rel, expected in EXPECTED.items():
    got = git_blob_sha((ROOT / rel).read_bytes())
    assert got == expected, (rel, got, expected)

sys.path.insert(0, str(ROOT))
subprocess.run(
    [sys.executable, "-m", "unittest", "canonical.tests.test_p1_causal_cutset_v6", "-v"],
    cwd=ROOT,
    check=True,
)

candidate = importlib.import_module("canonical.runtime.p1_causal_cutset_v6")
proof = importlib.import_module("canonical.runtime.p1_causal_cutset_v6_proof")
v5 = importlib.import_module("canonical.runtime.trajectory_failure_typed_ir_candidate_v5")

result = proof.prove(candidate)
assert result["pass"] is True, result
assert result["cross_product_cases"] == 192
assert result["false_earliest_alternative_cases"] == 6
assert result["total_cases"] == 198

for domain in proof.DOMAINS:
    case = proof.false_earliest_alternative_case(domain, "SCOPE", "STATE_TRANSITION")
    old = v5.solve(case)
    new = candidate.solve(case)
    assert old["status"] == "IDENTIFIED", (domain, old)
    assert old["cause_action_ids"] == ["A1"], (domain, old)
    assert old["mechanism_classes"] == ["SCOPE"], (domain, old)
    assert new["status"] == "IDENTIFIED", (domain, new)
    assert new["cause_action_ids"] == ["A4"], (domain, new)
    assert new["mechanism_classes"] == ["STATE_TRANSITION"], (domain, new)
    assert new["minimal_repair_check_ids"] == ["A4:STATE_TRANSITION"], (domain, new)
    assert proof.score(case["task"], new)["pass"] is True

gov=json.loads((ROOT/"canonical/governance/P1_EXECUTABLE_CAUSAL_CUTSET_V6.json").read_text())
assert gov["capability_credit_delta"] == 0
assert gov["family_credit_delta"] == 0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False
assert gov["terminal_results_replayed"] == 0
assert gov["new_reality_units_consumed"] == 0

print(json.dumps({
    "status":"PASS",
    "exact_brain_blobs":EXPECTED,
    "cross_product_cases":192,
    "false_earliest_alternative_cases":6,
    "total_cases":198,
    "v5_false_positive_reproduced_across_domains":6,
    "v6_executable_causal_cut_corrected_across_domains":6,
    "terminal_results_replayed":0,
    "new_reality_units_consumed":0,
    "capability_credit_delta":0,
    "family_credit_delta":0
}, sort_keys=True))
