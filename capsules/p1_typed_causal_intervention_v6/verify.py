from __future__ import annotations
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/runtime/trajectory_failure_typed_ir_candidate_v6.py": "18d4de68ee8352410e986c318868642333ec085a",
    "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py": "0f41a36e6ad16722ce05b180e036fb921a2ef886",
    "canonical/tests/test_trajectory_failure_typed_ir_v6.py": "6961f69cafd718da6dd439765a13f59ffc9790e1",
    "canonical/governance/P1_TYPED_CAUSAL_INTERVENTION_ENVELOPE_V6.json": "03df530cd77cd834de94b4e3c4588008bf4a8070",
}

def blob(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

for rel, want in EXPECTED.items():
    got = blob(ROOT / rel)
    assert got == want, (rel, got, want)

gov = json.loads((ROOT / "canonical/governance/P1_TYPED_CAUSAL_INTERVENTION_ENVELOPE_V6.json").read_text())
assert gov["envelope"]["cross_product_cases"] == 192
assert gov["envelope"]["nonambiguous_forward_rescue_cases"] == 144
assert gov["envelope"]["ambiguous_abstention_cases"] == 48
assert set(gov["targeted_residuals"]) == {
    "P1_EXPLICIT_SCOPE_FAILURE_CLASS",
    "P1_HETEROGENEOUS_INTERVENTION_RESCUE",
}
assert gov["new_reality_units_consumed"] == 0
assert gov["capability_credit_delta"] == 0
assert gov["family_credit_delta"] == 0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False

candidate_src = (ROOT / "canonical/runtime/trajectory_failure_typed_ir_candidate_v6.py").read_text()
assert "_oracle" not in candidate_src
assert "trajectory_failure_typed_ir_proof_v6" not in candidate_src

subprocess.run(
    [sys.executable, "-m", "unittest", "canonical.tests.test_trajectory_failure_typed_ir_v6", "-v"],
    cwd=ROOT, check=True
)

sys.path.insert(0, str(ROOT))
from canonical.runtime import trajectory_failure_typed_ir_candidate_v6 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof

cases = proof.suite_cases()
assert len(cases) == 192
passes = 0
rescued = 0
ambiguous = 0
scope_cases = 0
for case in cases:
    public = proof.public_task(case)
    assert "_oracle" not in public
    out = candidate.solve(public)
    verdict = proof.score_case(case, out)
    assert verdict["pass"] is True, (case["seed"], verdict, out)
    passes += 1
    if "SCOPE" in {k for ks in case["_oracle"]["mechanisms"].values() for k in ks}:
        scope_cases += 1
    if case["_oracle"]["status"] == "AMBIGUOUS":
        ambiguous += 1
        assert verdict["intervention_rescue_verified"] is False
    else:
        rescued += 1
        assert verdict["intervention_rescue_verified"] is True
        assert verdict["intervention"]["terminal_rescued"] is True

assert passes == 192
assert rescued == 144
assert ambiguous == 48
assert scope_cases >= 24

# Independent anti-shortcut checks.
interaction = proof.generate_case(91001, pattern="INTERACTION", domain="TOOL_API", kind="SCOPE")
interaction_out = candidate.solve(proof.public_task(interaction))
assert proof.score_case(interaction, interaction_out)["pass"] is True
partial = copy.deepcopy(interaction_out)
partial["repair_targets"] = partial["repair_targets"][:1]
assert proof.execute_intervention(proof.public_task(interaction), partial)["terminal_rescued"] is False
assert proof.score_case(interaction, partial)["pass"] is False

delayed = proof.generate_case(91002, pattern="DELAYED", domain="BROWSER", kind="PROVENANCE")
delayed_out = candidate.solve(proof.public_task(delayed))
symptom = copy.deepcopy(delayed_out)
symptom["repair_targets"] = ["restore:A4:INVARIANT"]
assert proof.execute_intervention(proof.public_task(delayed), symptom)["terminal_rescued"] is False

fake = copy.deepcopy(delayed_out)
fake["repair_targets"] = ["restore:A999:PROVENANCE"]
assert proof.execute_intervention(proof.public_task(delayed), fake)["terminal_rescued"] is False
assert proof.score_case(delayed, fake)["pass"] is False

oracle_mut = proof.generate_case(91003, pattern="SINGLE", domain="CODE", kind="SCOPE")
before = proof.public_task(oracle_mut)
oracle_mut["_oracle"]["critical"] = "A999"
after = proof.public_task(oracle_mut)
assert before == after

print(json.dumps({
    "status": "PASS",
    "exact_brain_blob_count": len(EXPECTED),
    "typed_case_count": passes,
    "scope_bearing_case_count": scope_cases,
    "forward_rescue_count": rescued,
    "ambiguous_abstention_count": ambiguous,
    "partial_interaction_repair_rescues": False,
    "symptom_only_repair_rescues": False,
    "fake_repair_string_rescues": False,
    "hidden_oracle_mutation_changes_public_payload": False,
    "new_reality_units_consumed": 0,
    "capability_credit_delta": 0,
    "family_credit_delta": 0,
}, indent=2, sort_keys=True))
