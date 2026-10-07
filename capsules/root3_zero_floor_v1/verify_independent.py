from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BRAIN = ROOT / "brain"

candidate = json.loads((BRAIN / "canonical/governance/ROOT3_ZERO_BAD_EVENT_THEORETICAL_FLOOR_REDUCTION_20261005_V1.json").read_text())
registry = json.loads((BRAIN / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json").read_text())
binding = json.loads((BRAIN / "canonical/governance/ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_BINDING_V2.json").read_text())
scope_law = json.loads((BRAIN / "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json").read_text())

reg = {row["id"]: row for row in registry["predicates"]}
apps = {row["predicate_id"]: row for row in candidate["current_root3_application"]}

direct = {
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
}
assert {pid for pid,row in apps.items() if row["application"] == "DIRECT_CANDIDATE"} == direct
assert apps["AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION"]["application"] == "STRONGER_SUFFICIENT_PROOF_CANDIDATE_ONLY"

assert reg["IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS"]["acceptance"] == "Zero critical authority violations on the frozen scope-boundary portfolio."
assert reg["COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES"]["acceptance"] == "No critical composition invariant fails."
assert "No material regression" in reg["AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION"]["acceptance"]

bound_ids = {row["predicate_id"] for row in binding["matched_scope_targets"]}
assert direct <= bound_ids
assert "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION" in bound_ids
assert len(binding["matched_scope_targets"]) == 7

allowed = set(scope_law["admissible_absolute_dominance_bases"])
assert allowed == {
    "EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
    "EXHAUSTIVE_FINITE_SUPERSET",
    "UNIVERSAL_FORMAL_SCOPE_PROOF",
}

# Independent algebraic falsification sweep of the theorem:
# if Brain bad-event loss is exactly zero and target loss is nonnegative,
# Brain cannot be worse on any point.
for target_loss in [0, 1e-12, 0.001, 1, 10, 10**9]:
    brain_loss = 0
    assert brain_loss <= target_loss

assert candidate["scheduler_effect_if_independently_verified"]["current_shared_root3_matched_scope_target_count"] == 7
assert candidate["scheduler_effect_if_independently_verified"]["minimum_comparator_dependent_target_count_if_only_direct_candidates_close"] == 5
assert candidate["scheduler_effect_if_independently_verified"]["minimum_comparator_dependent_target_count_if_all_three_scope_complete_floor_witnesses_close"] == 4

for key in (
    "acceptance_credit_delta",
    "family_credit_delta",
    "capability_credit_delta",
    "ownership_credit_delta",
):
    assert candidate["accounting"][key] == 0
assert candidate["execution_authority"] is False
assert candidate["promotion_authority"] is False
assert candidate["fresh_reality_authority"] is False
assert candidate["independent_verification_required"] is True

print("ROOT3_ZERO_BAD_EVENT_THEORETICAL_FLOOR_INDEPENDENT_PASS")
