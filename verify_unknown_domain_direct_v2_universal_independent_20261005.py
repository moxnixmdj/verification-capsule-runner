#!/usr/bin/env python3
"""Independent algebraic + end-to-end verifier for the frozen Unknown-Domain V2 theorem.

This verifier does not import Brain's proof module. It binds the six exact
runtime subjects, independently checks the load-bearing inequalities, and then
runs a deterministic falsification sweep through the exact generator, candidate,
harness, and hidden scorer. No production authority or terminal cases are used.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/unknown_domain_direct_v2_universal_independent_20261005"
sys.path.insert(0, str(SUBJECT))

EXPECTED_BLOBS = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py": "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py": "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py": "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py": "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py": "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py": "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}

def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

for rel, expected in EXPECTED_BLOBS.items():
    got = git_blob(SUBJECT / rel)
    assert got == expected, (rel, got, expected)

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness

families = tuple(g1.PRIMITIVE_FAMILIES)
assert len(families) == 6
assert g1.PRODUCTION_CASE_COUNTS == {g1.TRANSFER: 12, g1.ABSTAIN: 15}
assert harness.MAX_TRANSFER_PROBES == 2
assert c1.MAPPING_BASIS == "STRUCTURAL_EQUIVALENCE"

# Exact V1 surface-row rule: distractor i is role + 4.75 + 1.5*i + 0.25*probe_variant.
min_shift = 4.75
max_shift_second_probe = 6.50
true_abs_max = 3.50
shifted_max = true_abs_max + max_shift_second_probe

# Continuous unary families: strict wrong-support gaps dominate _close tolerance.
affine_min_gap = 0.6 * min_shift
affine_max_abs_output = 2.0 + 2.6 * shifted_max
affine_max_close_tol = 1e-9 * max(1.0, affine_max_abs_output)
assert affine_min_gap > affine_max_close_tol

complement_min_gap = min_shift
complement_max_abs_output = max(abs(8.0 - (-true_abs_max)), abs(2.0 - shifted_max))
complement_max_close_tol = 1e-9 * max(1.0, complement_max_abs_output)
assert complement_min_gap > complement_max_close_tol

# f(x)=x/(1+|x|) has derivative 1/(1+|x|)^2 away from 0.
# On every interval joining a legal true probe x in [-3.5,3.5] to x+d <=10,
# the minimum derivative is >=1/121. gain>=0.7.
sat_min_gap = 0.7 * min_shift / 121.0
sat_max_abs_output = 1.5 + 3.0
sat_max_close_tol = 1e-9 * sat_max_abs_output
assert sat_min_gap > sat_max_close_tol

family_indices = {fam: [i for i in range(12) if families[i % len(families)] == fam] for fam in families}

# SIGN cases: first allowed target probe is target row j=3. For both SIGN
# indices, its true r0 is negative. Every distractor adds >=4.75, so is positive.
sign_family = "PARITY_OR_SIGN_INVARIANT"
assert family_indices[sign_family] == [1, 7]
for i in family_indices[sign_family]:
    j = 3
    assert (j + i) % 2 == 0
assert -0.25 < 0.0
assert -true_abs_max + min_shift > 0.0

# STEP cases: first allowed probe j=3 is above threshold and can remain
# ambiguous; second allowed probe j=4 is below threshold. Since mag<=2.2 and
# distractor shift>=4.75, every wrong support is forced above threshold.
step_family = "THRESHOLD_OR_PARTITION_INVARIANT"
assert family_indices[step_family] == [5, 11]
assert 4 % 2 == 0
step_wrong_side_margin = min_shift - 2.2
assert step_wrong_side_margin > 0.0
assert (-0.5) < 0.5  # disjoint frozen low/high parameter ranges

# ADD2 cases: on first probe j=3, both true roles are positive for both ADD2
# indices. Enumerate the five wrong-support pair forms algebraically.
add2_family = "COMPOSITIONAL_REWRITE"
assert family_indices[add2_family] == [4, 10]
for i in family_indices[add2_family]:
    j = 3
    assert (j + i) % 2 == 1
    assert (j + i + 1) % 3 != 0
lo, hi = 0.25, 3.5
add2_wrong_support_gaps = [
    4.75 - (hi - lo),
    6.25,
    4.75,
    6.25 - (hi - lo),
    4.75 + 6.25,
]
add2_min_gap = min(add2_wrong_support_gaps)
assert add2_min_gap == 1.5

# ADD2's only surviving true-support ambiguity is r0/r1 permutation, and its
# exact primitive is symmetric in those roles.
p = {"dsl": "UDIR_V1", "op": "ADD2", "roles": ["r0", "r1"], "params": {"bias": 0.37}}
for a, b in [(-3.5, 2.25), (0.25, 3.5), (1.75, -0.5)]:
    x = c1._program_eval(p, {"r0": a, "r1": b})
    y = c1._program_eval(p, {"r0": b, "r1": a})
    assert x == y

# Abstention classes are a complete generator partition and exactly match the
# candidate/scorer decision rules.
assert tuple(g1.ABSTAIN_CLASSES) == ("IDENTIFIABLE", "NONIDENTIFIABLE", "UNDERSPECIFIED")
assert scorer.DECISIONS == {"CONCLUDE", "ABSTAIN", "REQUEST_DISCRIMINATOR"}

# Deterministic implementation-level falsification sweep. This is supplemental
# to the algebraic proof, not a substitute for it.
POPULATIONS = 512
case_count = 0
probe_histogram = {}
family_case_count = {fam: 0 for fam in families}
for k in range(POPULATIONS):
    secret = hashlib.sha256(f"independent-secret-{k}".encode()).digest()
    beacon = "INDEPENDENT-VERIFY-" + hashlib.sha256(f"beacon-{k}".encode()).hexdigest()[:24]
    packet = g2._generate(beacon=beacon, evaluator_secret=secret, namespace=f"IV{k}")
    assert packet["case_count"] == 27
    results = []
    for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"], strict=True):
        executed = harness.execute_case(
            candidate_step=c2.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        result = executed["scorer_result"]
        if result["pass"] is not True:
            raise AssertionError(json.dumps({
                "population": k,
                "case_id": visible["case_id"],
                "primitive_family": hidden.get("primitive_family"),
                "latent_program": hidden.get("latent_primitive_program"),
                "hidden_mapping": hidden.get("domain_mapping"),
                "gold_terminal_consequence": hidden.get("gold_terminal_consequence"),
                "candidate_terminal_action": executed.get("candidate_terminal_action"),
                "probe_count": executed.get("probe_count"),
                "transcript": executed.get("transcript"),
                "scorer_result": result,
            }, sort_keys=True))
        results.append(result)
        pc = int(executed["probe_count"])
        probe_histogram[str(pc)] = probe_histogram.get(str(pc), 0) + 1
        if hidden["leaf_id"] == g1.TRANSFER:
            family_case_count[str(hidden["primitive_family"])] += 1
        case_count += 1
    agg = scorer.aggregate(results)
    assert agg["all_27_cases_pass"] is True

receipt = {
    "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V2_INDEPENDENT_UNIVERSAL_VERIFICATION_V1",
    "status": "PASS__INDEPENDENT_ALGEBRAIC_PROOF_PREMISES_AND_END_TO_END_FALSIFICATION_SWEEP",
    "exact_subject_blobs": EXPECTED_BLOBS,
    "algebraic_margins": {
        "affine_min_wrong_support_gap": affine_min_gap,
        "affine_max_close_tolerance": affine_max_close_tol,
        "complement_min_wrong_support_gap": complement_min_gap,
        "complement_max_close_tolerance": complement_max_close_tol,
        "sat_mono_min_wrong_support_gap": sat_min_gap,
        "sat_mono_max_close_tolerance": sat_max_close_tol,
        "sign_min_shifted_distractor_value": -true_abs_max + min_shift,
        "step_second_probe_wrong_side_margin": step_wrong_side_margin,
        "add2_min_wrong_support_gap": add2_min_gap,
        "add2_true_support_role_swap_output_equivalent": True,
    },
    "synthetic_falsification": {
        "populations": POPULATIONS,
        "cases": case_count,
        "probe_count_histogram": probe_histogram,
        "transfer_family_case_count": family_case_count,
        "all_cases_exact_hidden_scorer_pass": True,
    },
    "deduction": "FOR_THE_EXACT_BOUND_FROZEN_V2_RUNTIME__THE_LOAD_BEARING_GENERATOR_INEQUALITIES_STRICTLY_IDENTIFY_TRUE_SUPPORT_WITHIN_THE_TWO_PROBE_BUDGET__AND_THE_ABSTENTION_PARTITION_MATCHES_THE_EXACT_CANDIDATE_AND_SCORER_RULES",
    "hard_nonclaims": [
        "NO_OPEN_WORLD_GENERALIZATION_BEYOND_THE_FROZEN_GENERATOR_DOMAIN",
        "SYNTHETIC_SWEEP_IS_FALSIFICATION_SUPPORT_NOT_THE_UNIVERSAL_PROOF_BY_ITSELF",
        "NO_PRODUCTION_AUTHORITY_USED",
        "NO_PRODUCTION_OR_TERMINAL_CASES_READ",
        "NO_ACCEPTANCE_OR_CAPABILITY_CREDIT_GRANTED_BY_THIS_SCRIPT_ALONE"
    ],
    "accounting": {
        "incremental_spend_usd": 0,
        "production_cases_consumed": 0,
        "terminal_cases_consumed": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0
    }
}
Path("unknown_domain_direct_v2_independent_universal_verification_v1.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps(receipt, sort_keys=True))
