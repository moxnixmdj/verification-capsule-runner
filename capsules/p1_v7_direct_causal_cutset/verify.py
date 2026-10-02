from __future__ import annotations
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BRAIN = ROOT / "brain"
sys.path.insert(0, str(BRAIN))

EXPECTED = {
    "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py": "9604a7f0e67e9278abc5ee6402a387c81c7b934e",
    "canonical/runtime/trajectory_failure_typed_ir_proof_v7.py": "8ef4ebe5e1a3404e5d6eaa4d63988651b6c44c1d",
    "canonical/tests/test_trajectory_failure_typed_ir_v7.py": "22addf0014ea44b71370a3a4371193a29a3a5514",
    "canonical/governance/P1_TYPED_DIRECT_CAUSAL_CUTSET_ENVELOPE_V7.json": "f035703c52acb10bfd0f92adf58fade89c49bf5b",
    "canonical/runtime/trajectory_failure_typed_ir_candidate_v6.py": "18d4de68ee8352410e986c318868642333ec085a",
    "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py": "0f41a36e6ad16722ce05b180e036fb921a2ef886",
}

def blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

for rel, expected in EXPECTED.items():
    got = blob_sha(BRAIN / rel)
    assert got == expected, (rel, got, expected)

from canonical.runtime import trajectory_failure_typed_ir_candidate_v6 as v6
from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as v7
from canonical.runtime import trajectory_failure_typed_ir_proof_v7 as proof

suite = unittest.defaultTestLoader.loadTestsFromName(
    "canonical.tests.test_trajectory_failure_typed_ir_v7"
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful(), "Brain V7 test suite failed"

# Independent check 1: preserve all 192 V6 cross-product cases.
cross = proof.suite_cases()
assert len(cross) == 192
rescued = ambiguous = 0
for case in cross:
    out = v7.solve(proof.public_task(case))
    verdict = proof.score_case(case, out)
    assert verdict.get("pass") is True, (case.get("seed"), out, verdict)
    if case["_oracle"]["status"] == "AMBIGUOUS":
        ambiguous += 1
    else:
        rescued += 1
assert (rescued, ambiguous) == (144, 48)

# Independent check 2: reproduce V6 derived-only overclaim and require V7 abstention.
for domain in proof.DOMAINS:
    public = proof.derived_only_case(domain)
    old = v6.solve(public)
    new = v7.solve(public)
    assert old.get("status") == "IDENTIFIED", (domain, old)
    assert new == {
        "status": "ESCALATE",
        "reason": "ONLY_DERIVED_UPSTREAM_FAILURES_VISIBLE__NO_DIRECT_CAUSAL_ROOT_PROVED",
    }, (domain, new)
    assert proof.execute_intervention(public, new).get("terminal_rescued") is False

# Independent check 3: reproduce V6 serial co-fault miss and require the full V7 cutset.
for domain in proof.DOMAINS:
    public = proof.serial_direct_cofault_case(domain)
    old = v6.solve(public)
    old_iv = proof.execute_intervention(public, old)
    assert old_iv.get("terminal_rescued") is False, (domain, old, old_iv)

    new = v7.solve(public)
    assert new.get("status") == "INTERACTION", (domain, new)
    assert new.get("cause_action_ids") == ["A1", "A2"], (domain, new)
    assert new.get("repair_targets") == ["restore:A1:AUTHORITY", "restore:A2:SCOPE"], (domain, new)
    new_iv = proof.execute_intervention(public, new)
    assert new_iv.get("terminal_rescued") is True, (domain, new, new_iv)

# Independent check 4: if the later fault is explicitly derived, it must leave the cutset.
public = proof.serial_direct_cofault_case("CODE")
for row in public["task"]["trajectory"]:
    if row["action_id"] == "A2":
        for check in row["checks"]:
            if check.get("pass") is False:
                check["failure_semantics"] = "DERIVED_UPSTREAM"
new = v7.solve(public)
assert new.get("status") == "IDENTIFIED", new
assert new.get("cause_action_ids") == ["A1"], new
assert new.get("repair_targets") == ["restore:A1:AUTHORITY"], new
assert proof.execute_intervention(public, new).get("terminal_rescued") is True

# Independent check 5: fail closed if a failed check lacks explicit semantics.
public = proof.serial_direct_cofault_case("RESEARCH")
for row in public["task"]["trajectory"]:
    for check in row["checks"]:
        if check.get("pass") is False:
            check.pop("failure_semantics", None)
            bad = v7.solve(public)
            assert bad.get("status") == "FAIL_CLOSED", bad
            break
    else:
        continue
    break

gov = json.loads((BRAIN / "canonical/governance/P1_TYPED_DIRECT_CAUSAL_CUTSET_ENVELOPE_V7.json").read_text())
assert gov["candidate"]["git_blob_sha"] == EXPECTED["canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py"]
assert gov["proof"]["git_blob_sha"] == EXPECTED["canonical/runtime/trajectory_failure_typed_ir_proof_v7.py"]
assert gov["tests"]["git_blob_sha"] == EXPECTED["canonical/tests/test_trajectory_failure_typed_ir_v7.py"]
assert gov["capability_credit_delta"] == 0
assert gov["family_credit_delta"] == 0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False

print(json.dumps({
    "status": "PASS",
    "exact_blob_count": len(EXPECTED),
    "brain_tests_run": result.testsRun,
    "v6_cross_product_cases_preserved": len(cross),
    "forward_rescues_preserved": rescued,
    "ambiguity_abstentions_preserved": ambiguous,
    "derived_only_counterexamples_killed": len(proof.DOMAINS),
    "serial_direct_cofault_counterexamples_killed": len(proof.DOMAINS),
    "terminal_case_ids_consumed": 0,
    "terminal_seeds_consumed": 0,
    "new_reality_units_consumed": 0,
    "capability_credit_delta": 0,
    "family_credit_delta": 0,
}, indent=2, sort_keys=True))
