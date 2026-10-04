from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "subject" / "root2_19_post_livebench_revocation_reactivation_v1_20261004"

FILES = {
    "candidate": SUB / "ROOT2_19_PREDICATE_POST_LIVEBENCH_REVOCATION_REACTIVATION_V1.json",
    "root": SUB / "TERMINAL_ROOT_CAUSE_STATE_V1.json",
    "activation": SUB / "ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_ACTIVATION_V1.json",
    "subject_verification": SUB / "ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
    "prior_activation_verification": SUB / "ROOT2_OUTPUT_ONLY_THRESHOLD_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
    "revocation": SUB / "LIVEBENCH_FORCED_FAIL_ROOT1_REVOCATION_20261004_V1.json",
    "scorer_scope": SUB / "LIVEBENCH_TERMINAL_SCORER_SCOPE_ACTIVATION_V1.json",
}

EXPECTED = {
    "candidate": "2290a4e553cc0d685fc2a0ecaefe8621fea1c206",
    "root": "e8371418ed39b83b14df874c8eb5e0bdb6a2e603",
    "activation": "7ea4dd4edb59c8526bd3993e02f4a8fb53c65085",
    "subject_verification": "553602570334f39003708e52d781b8c59f27eb7c",
    "prior_activation_verification": "eef494009e47b758a99ab48649e050c332e4988a",
    "revocation": "bbbe29ec26b1f96ba5538ca159f899e316b167e7",
    "scorer_scope": "f64fe4a10c3b7f8a8a95819fb79c898d17a2bae4",
}

EXPECTED_ROOT2 = {
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
    "AUTOMATIONBENCH_GE_40",
    "CHARTOGRAPHY_TOOLS_GE_89",
    "CODING_CURSORBENCH_GE_57_8",
    "CODING_FRONTIERCODE_GE_54_4",
    "CODING_TB4_GE_66_4",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
    "FINANCE_ACCOUNTING_INDEX_GE_61",
    "FINANCE_AGENT_V2_GE_58_59",
    "HLE_TOOLS_GE_67_7",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "LIVEBENCH_IF_GE_65_7",
    "MYSTERYMECHANISM_GE_49_55",
    "OSWORLD_2_1_PARTIAL_GE_81_8",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "PROWORK_GDPVAL_GE_1846",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
    "TB_SCIENCE_GE_58_7",
}

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

for key, path in FILES.items():
    actual = git_blob_sha(path)
    assert actual == EXPECTED[key], (key, actual, EXPECTED[key])

candidate = json.loads(FILES["candidate"].read_text())
root = json.loads(FILES["root"].read_text())
activation = json.loads(FILES["activation"].read_text())
subject_verification = json.loads(FILES["subject_verification"].read_text())
prior_activation_verification = json.loads(FILES["prior_activation_verification"].read_text())
revocation = json.loads(FILES["revocation"].read_text())
scorer_scope = json.loads(FILES["scorer_scope"].read_text())

assert candidate["schema"] == "PROJECT_BRAIN_ROOT2_19_PREDICATE_POST_LIVEBENCH_REVOCATION_REACTIVATION_V1"
assert candidate["current_root_binding"]["git_blob_sha"] == EXPECTED["root"]
assert candidate["reused_verified_controller"]["activation_git_blob_sha"] == EXPECTED["activation"]
assert candidate["reused_verified_controller"]["subject_verification_git_blob_sha"] == EXPECTED["subject_verification"]
assert candidate["reused_verified_controller"]["prior_activation_verification_git_blob_sha"] == EXPECTED["prior_activation_verification"]
assert candidate["livebench_truth_repair"]["revocation_git_blob_sha"] == EXPECTED["revocation"]
assert candidate["livebench_truth_repair"]["scorer_scope_activation_git_blob_sha"] == EXPECTED["scorer_scope"]
assert candidate["authority"] == {
    "scheduling": False,
    "execution": False,
    "promotion": False,
    "fresh_reality": False,
    "acceptance_credit": False,
}

current = root["current_acceptance"]
assert current["accepted_families"] == 5
assert current["open_families"] == 14
assert current["proved_atomic"] == 12
assert current["unresolved_atomic"] == 26
assert current["terminal"] is False

partition = root["current_residual_root_partition"]
assert partition["root1_positive_gap_count"] == 0
assert partition["root2_only_count"] == 16
assert partition["root3_only_count"] == 7
assert partition["root2_and_root3_count"] == 3
root2 = set(partition["root2_only"]) | set(partition["root2_and_root3"])
assert len(root2) == 19
assert root2 == EXPECTED_ROOT2
assert set(candidate["current_root_binding"]["exact_root2_touching_predicates"]) == EXPECTED_ROOT2

policy = root["scheduler_policy"]
assert policy["root2_effective_scheduling_authority"] is False
assert policy["root2_effective_scheduling_scope"] == "PENDING_EXACT_CURRENT_19_ROOT2_TOUCHING_RECOMPUTE"

assert subject_verification["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert subject_verification["verified"]["predicate_count"] == 19
assert subject_verification["verified"]["transitive_fresh_reality_blocking"] is True
assert subject_verification["verified"]["overlapping_coverage_double_count_rejected"] is True
assert subject_verification["verified"]["execution_authority"] is False

assert prior_activation_verification["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert prior_activation_verification["verified"]["root2_touching_predicates"] == 19
assert prior_activation_verification["verified"]["root1_positive_gaps"] == 0
assert prior_activation_verification["verified"]["output_only_threshold_scheduling_bound"] is True
assert prior_activation_verification["verified"]["fresh_reality_block_preserved"] is True

assert activation["authority"] == {
    "scheduling": True,
    "execution": False,
    "promotion": False,
    "fresh_reality": False,
}
assert activation["current_root_precondition"]["root2_touching_predicates"] == 19

assert revocation["status"].startswith("ACTIVE_FAIL_CLOSED_TRUTH_REPAIR")
proj = revocation["corrected_current_projection"]
assert proj["livebench_class"] == "ROOT2_ONLY__MEASUREMENT_OR_COMPARATOR_UNCERTAINTY"
assert proj["root1_positive_gap_count"] == 0
assert proj["root2_only"] == 16
assert proj["root3_only"] == 7
assert proj["root2_and_root3"] == 3
assert "LIVEBENCH_V6_FORCED_FAIL_BINDING_V1" in " ".join(revocation["scheduler_override"])

assert scorer_scope["target_predicate"] == "LIVEBENCH_IF_GE_65_7"
truth = scorer_scope["activated_scheduler_truth"]
assert truth["active_scorer_family"] == "LEGACY_IFEVAL_ONLY"
assert truth["active_population_count"] == 200
assert truth["load_bearing_checker_registry_count"] == 25
assert truth["modern_ifbench_checker_count_on_exact_frozen_critical_path"] == 0

rules = set(candidate["hard_rules"])
assert "NO_REUSE_OF_LIVEBENCH_V6_FORCED_FAIL_BINDING_V1_AS_PASS_OR_FAIL_EVIDENCE" in rules
assert "NO_EXECUTION_PROMOTION_OR_FRESH_REALITY_AUTHORITY" in rules
assert candidate["accounting"]["acceptance_credit_delta"] == 0
assert candidate["accounting"]["capability_credit_delta"] == 0
assert candidate["accounting"]["ownership_credit_delta"] == 0

print("PASS: exact corrected 19-predicate Root2 partition safely rebinds to the independently verified output-only threshold DAG")
