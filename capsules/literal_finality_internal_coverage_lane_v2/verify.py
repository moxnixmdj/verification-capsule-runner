import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def load(name):
    with (ROOT / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)

def git_blob(name):
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / name)],
        text=True,
    ).strip()

m = load("manifest.json")
for name, expected in m["exact_blobs"].items():
    got = git_blob(name)
    assert got == expected, (name, expected, got)

v2 = load("subject.json")
v1 = load("v1.json")
fixed = load("fixed_interface.json")
guard = load("role_guard.json")
guard_verify = load("role_guard_verification.json")
imp = load("impossibility_repair.json")
imp_verify = load("impossibility_verification.json")

assert v1["minimum_action_policy"]["literal_finality_lane"] == "SLEEP_EVENT_DRIVEN"
assert "ZERO_INFORMATION_POSITIVE_INTERNAL" in v1["breakthrough"]["new_state"]

assert fixed["status"].startswith("CANDIDATE__FIXED_INTERFACE_TRACE_SUPERSET_COVERAGE")
premises = fixed["trace_normal_form"]["theorem"]["premises"]
assert len(premises) == 3
assert fixed["critical_path_effect"]["remaining_load_bearing_problem"]

assert guard["status"].startswith("CANDIDATE__FUNCTIONAL_ROLE_COVERAGE_IS_NOT_YET_LITERAL_USEFUL_BEHAVIOR_COVERAGE")
assert any("SEMANTIC_TOTALITY" in x for x in guard["admissible_completion_routes"])
assert "NO_CLAIM_CURRENT_19_FAMILY_UNION_CANNOT_EVENTUALLY_PROVE_TOTALITY" in guard["hard_nonclaims"]
assert guard_verify["status"].startswith("CONNECTOR_RECOMPUTATION_PASS")
assert guard_verify["recomputation"]["errors"] == []

assert imp["status"].startswith("TRUTH_REPAIRED__FIXED_POLICY_OBSTRUCTION_ONLY")
assert "USE_THIS_FILE_TO_BLOCK_ALL_TARGET_INDEPENDENT_ROUTE_C_WORK" in imp["scheduler_effect"]["delete"]
assert imp_verify["status"].startswith("INDEPENDENT_SYMBOLIC_KERNEL_PASS")
assert "ROUTE_C_CONFIGURABLE_CAPABILITY_DOMINANCE_IS_CLOSED" in imp_verify["does_not_verify"]

assert v2["schema"] == "PROJECT_BRAIN_LITERAL_TERMINAL_NOW_ATTAINABILITY_CUT_V2"
assert v2["supersedes"]["git_blob_sha"] == m["exact_blobs"]["v1.json"]
assert v2["newer_authorities"]["fixed_interface_coverage_candidate"]["git_blob_sha"] == m["exact_blobs"]["fixed_interface.json"]
assert v2["newer_authorities"]["functional_role_guard"]["git_blob_sha"] == m["exact_blobs"]["role_guard.json"]
assert v2["newer_authorities"]["functional_role_guard_verification"]["git_blob_sha"] == m["exact_blobs"]["role_guard_verification.json"]
assert v2["newer_authorities"]["target_agnostic_impossibility_truth_repair"]["git_blob_sha"] == m["exact_blobs"]["impossibility_repair.json"]
assert v2["newer_authorities"]["target_agnostic_impossibility_symbolic_verification"]["git_blob_sha"] == m["exact_blobs"]["impossibility_verification.json"]

lane = v2["literal_finality_lane"]
assert lane["state"] == "CONDITIONAL_INTERNAL_PROOF_LANE"
assert lane["terminal_finality"] is False
assert lane["coverage_certificate_proved"] is False
assert lane["domain_dominance_proved"] is False
ids = {x["id"] for x in lane["admitted_actions"]}
assert ids == {
    "COVERAGE_P1_INTERFACE_COMPLETENESS",
    "COVERAGE_P2_ROLE_CLASSIFICATION_TOTALITY",
    "COVERAGE_P3_ROLE_TO_FAMILY_SEMANTIC_TOTALITY",
    "DOMINANCE_AFTER_COVERAGE",
}
dom = next(x for x in lane["admitted_actions"] if x["id"] == "DOMINANCE_AFTER_COVERAGE")
assert dom["action"].startswith("ONLY_AFTER_P1_P2_P3_ARE_INDEPENDENTLY_PROVED")
assert "GENERIC_BENCHMARK_ACCUMULATION_FOR_LITERAL_COMPLETENESS" in lane["forbidden_actions"]
assert "FINITE_BLACK_BOX_QUERY_EXPANSION_FOR_LITERAL_COMPLETENESS" in lane["forbidden_actions"]

# The truth repair is scheduler-only. It must never mint capability or terminal credit.
for key, value in v2["accounting"].items():
    assert value == 0, (key, value)
assert v2["scheduling_authority"] is False
assert v2["execution_authority"] is False
assert v2["promotion_authority"] is False
assert v2["fresh_reality_authority"] is False
assert v2["independent_verification_required"] is True
assert "NO_CLAIM_TERMINAL_GOAL_IS_ACHIEVED" in v2["hard_nonclaims"]

# Constructive existence witness for internal proof-state work:
# P2/P3 are explicit completion routes over already-bound canonical semantics,
# while the independently verified impossibility correction explicitly revokes
# the blanket block on target-independent configurable Route C.
assert {
    "COVERAGE_P2_ROLE_CLASSIFICATION_TOTALITY",
    "COVERAGE_P3_ROLE_TO_FAMILY_SEMANTIC_TOTALITY",
}.issubset(ids)
assert "USE_THIS_FILE_TO_BLOCK_ALL_TARGET_INDEPENDENT_ROUTE_C_WORK" in imp["scheduler_effect"]["delete"]

print("LITERAL_FINALITY_V2_INTERNAL_COVERAGE_LANE_VERIFIED")
