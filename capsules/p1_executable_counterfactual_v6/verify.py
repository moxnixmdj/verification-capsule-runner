from __future__ import annotations

import copy
import hashlib
import inspect
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
M = json.loads((ROOT / "EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))


def blob_sha(path: pathlib.Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\\0" + b).hexdigest()


for rel, expected in M["exact_brain_blobs"].items():
    actual = blob_sha(ROOT / rel)
    assert actual == expected, (rel, actual, expected)

subprocess.run(
    [
        sys.executable,
        "-m",
        "py_compile",
        str(ROOT / "canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py"),
        str(ROOT / "canonical/runtime/trajectory_failure_executable_counterfactual_proof_v6.py"),
    ],
    check=True,
)
subprocess.run(
    [
        sys.executable,
        "-m",
        "unittest",
        "canonical.tests.test_trajectory_failure_executable_counterfactual_v6",
        "-v",
    ],
    cwd=ROOT,
    check=True,
)

sys.path.insert(0, str(ROOT))
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_executable_counterfactual_proof_v6 as proof

source = inspect.getsource(proof.evaluate_intervention)
assert "_oracle" not in source, source
assert "required_root_repairs" not in source, source
assert "_execute_world" in source, source

expected = M["expected"]
cases = proof.suite_cases()
assert len(cases) == expected["cross_product_case_count"], len(cases)

passes = 0
rescues = 0
interactions = 0
ambiguous = 0
scope_cases = 0
symptom_rejections = 0
ambiguous_vectors = set()

for case in cases:
    public = proof.public_task(case)
    assert "_oracle" not in public
    assert "_worlds" not in public
    assert "latent_faults" not in repr(public)
    assert "alternative_selector" not in repr(public)

    baseline = proof.evaluate_intervention(case, [])
    assert baseline["any_world_terminal_success"] is False, (case["seed"], baseline)

    out = candidate.solve(public)
    verdict = proof.score_case(case, out)
    assert verdict["pass"] is True, (case["seed"], case["pattern"], verdict, out)
    passes += 1

    if case["_oracle"]["mechanisms"]["A1"][0] == "SCOPE":
        scope_cases += 1

    if out["status"] in {"IDENTIFIED", "INTERACTION"}:
        iv = proof.evaluate_intervention(case, out["repair_targets"])
        assert iv["all_worlds_terminal_success"] is True, (case["seed"], iv)
        rescues += 1

        symptoms = proof._symptom_repairs(case)
        assert symptoms
        symptom_iv = proof.evaluate_intervention(case, symptoms)
        assert symptom_iv["any_world_terminal_success"] is False, (case["seed"], symptom_iv)
        symptom_rejections += 1

    if out["status"] == "INTERACTION":
        interactions += 1
        for repair in out["repair_targets"]:
            partial = proof.evaluate_intervention(case, [repair])
            assert partial["any_world_terminal_success"] is False, (case["seed"], repair, partial)

    if out["status"] == "AMBIGUOUS":
        ambiguous += 1
        assert len(case["_worlds"]) == 2
        local_vectors = []
        for aid, kinds in case["_oracle"]["mechanisms"].items():
            for kind in kinds:
                iv = proof.evaluate_intervention(case, [f"restore:{aid}:{kind}"])
                vector = tuple(bool(x["terminal_success"]) for x in iv["world_results"])
                local_vectors.append(vector)
                ambiguous_vectors.add(vector)
                assert any(vector) and not all(vector), (case["seed"], vector)
        assert set(local_vectors) == {(True, False), (False, True)}, (case["seed"], local_vectors)

assert passes == expected["cross_product_case_count"]
assert rescues == expected["identified_or_interaction_rescue_count"]
assert interactions == expected["interaction_case_count"]
assert ambiguous == expected["ambiguous_case_count"]
assert scope_cases == expected["explicit_scope_root_case_count"]
assert symptom_rejections == expected["identified_or_interaction_rescue_count"]
assert ambiguous_vectors == {(True, False), (False, True)}

# Prove intervention execution is independent of the expected-label oracle.
probe = proof.generate_case(880001, pattern="DELAYED", domain="CODE", kind="SCOPE")
repair = ["restore:A1:SCOPE"]
before = proof.evaluate_intervention(probe, repair)
mutated = copy.deepcopy(probe)
mutated["_oracle"] = {
    "status": "AMBIGUOUS",
    "roots": ["A999"],
    "critical": None,
    "mechanisms": {"A999": ["AUTHORITY"]},
}
after = proof.evaluate_intervention(mutated, repair)
assert before == after
assert before["all_worlds_terminal_success"] is True

# Prove hidden structural faults are load-bearing to terminal outcome.
structural = copy.deepcopy(probe)
for world in structural["_worlds"]:
    world["latent_faults"] = {}
without_fault = proof.evaluate_intervention(structural, [])
assert without_fault["all_worlds_terminal_success"] is True

gov = json.loads(
    (ROOT / "canonical/governance/P1_EXECUTABLE_COUNTERFACTUAL_ENVELOPE_V6.json").read_text(
        encoding="utf-8"
    )
)
assert gov["residual_targeted"] == "P1_HETEROGENEOUS_INTERVENTION_RESCUE"
assert gov["scope"]["cross_product_case_count"] == 192
assert gov["new_reality_units_consumed"] == 0
assert gov["capability_credit_delta"] == 0
assert gov["family_credit_delta"] == 0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False

print(
    json.dumps(
        {
            "status": "PASS",
            "exact_brain_blob_count": len(M["exact_brain_blobs"]),
            "cross_product_case_count": passes,
            "identified_or_interaction_executable_rescue_count": rescues,
            "interaction_partial_repair_rejection_count": interactions,
            "symptom_only_repair_rejection_count": symptom_rejections,
            "ambiguous_two_world_case_count": ambiguous,
            "explicit_scope_root_case_count": scope_cases,
            "intervention_evaluator_reads_oracle": False,
            "intervention_evaluator_reads_required_repair_set": False,
            "hidden_structural_faults_load_bearing": True,
            "new_reality_units_consumed": 0,
            "credit_delta": 0,
        },
        indent=2,
        sort_keys=True,
    )
)
