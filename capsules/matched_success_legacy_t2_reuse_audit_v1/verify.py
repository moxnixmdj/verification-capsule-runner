from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "source"
AUTH = ROOT / "authority"

BLOBS = {
    SRC / "MATCHED_SUCCESS_LEGACY_T2_REUSE_AUDIT_V1.json": "43d2b820ac1389c7e1e76f907acf2f6f11311607",
    SRC / "matched_success_legacy_t2_reuse_audit_v1.py": "6051f2fef40bbcc7f5971128e4fb5eb87f09f7e4",
    AUTH / "OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json": "72a5cd689f55df84de73693371264f02ef4e7226",
    AUTH / "BROWSER_T2_OBJECTIVE_TERMINAL_BINDING_V1.json": "28e955d5d593d1de9cfab0f9cdcdae732fd315f1",
    AUTH / "DELEGATION_T2_OBJECTIVE_TERMINAL_BINDING_V1.json": "a1e441567b132d71713ed55dfc51f01d8de112d1",
    AUTH / "TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json": "6bcabc0a7d0525532ce7b80e132278f7c99caa43",
    AUTH / "M0_PORTFOLIO_MULTIPLEX_TERMINAL_BINDING_V1.json": "d34a284f7c1f99fd93d420f3a5aba93851b29ef6",
    AUTH / "P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json": "8703c6aa08227467a619a7ae90d0d61f8e54da39",
    AUTH / "TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json": "a1630299d29ea9c07e55b4314c07ddb3228c3287",
    AUTH / "terminal_parent_portfolio_runner_v1.py": "431b62e503a6a179f19339ae5e0ab6948424a650",
}


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


for path, expected in BLOBS.items():
    assert git_blob(path) == expected, (path, git_blob(path), expected)


def load(name: str):
    return json.loads((AUTH / name).read_text())


audit = json.loads((SRC / "MATCHED_SUCCESS_LEGACY_T2_REUSE_AUDIT_V1.json").read_text())
norm = load("OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json")
browser = load("BROWSER_T2_OBJECTIVE_TERMINAL_BINDING_V1.json")
delegation = load("DELEGATION_T2_OBJECTIVE_TERMINAL_BINDING_V1.json")
tool = load("TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json")
m0 = load("M0_PORTFOLIO_MULTIPLEX_TERMINAL_BINDING_V1.json")
p1 = load("P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json")
runner_binding = load("TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json")
runner_text = (AUTH / "terminal_parent_portfolio_runner_v1.py").read_text()

TARGETS = {
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}

all_atoms = {
    src["atom"]
    for target in norm["targets"]
    if target["predicate_id"] in TARGETS
    for src in target["atom_sources"]
    if src["atom"].startswith("dimension:")
}
assert len(all_atoms) == 16

browser_classes = set(browser["direct_objective_source_pool"]["class_cycle"])
browser_dims = set(browser["objective_dimensions"])
delegation_classes = set(delegation["source_pool"]["class_cycle"])
delegation_dims = set(delegation["objective_dimensions"])
tool_classes = set(tool["source_pool"]["class_cycle"])
tool_dims = set(tool["objective_dimensions"])
m0_checks = set(m0["evaluator"]["required_checks"])
p1_checks = set(p1["evaluator"]["required_checks"])

derived_supported = set()

if (
    "STALE_REBIND" in browser_classes
    and "FRESH_STATE_CONDITIONING" in browser_dims
    and {
        "V2_WORKER_CAPABILITY_REMOVED",
        "V2_RESOURCE_CAPACITY_CHANGED",
    }.issubset(delegation_classes)
    and {
        "SELECTED_TOOL_LOSES_CAPABILITY",
        "CHEAPER_TOOL_GAINS_CAPABILITY",
    }.issubset(tool_classes)
):
    derived_supported.add("dimension:state_change_after_actions_requiring_replanning")

if (
    "OBSERVABLE_MISMATCH_RECOVERY" in browser_dims
    and {
        "SELECTED_TOOL_LOSES_CAPABILITY",
        "CHEAPER_TOOL_UNAVAILABLE",
    }.issubset(tool_classes)
    and "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE" in p1_checks
):
    derived_supported.add("dimension:tool_failure_and_recovery")

if (
    "DEPENDENCY_RESPECTING_FANOUT_FANIN" in delegation_dims
    and {
        "V3_FORK_JOIN",
        "V3_FANOUT_JOIN",
        "V3_DUAL_ROOT_FANIN",
    }.issubset(delegation_classes)
):
    derived_supported.add("dimension:subtask_dependency_and_fan_in")

if (
    "ACTIVE_CONSTRAINT_ADMISSIBILITY" in tool_dims
    and "CHEAPER_TOOL_UNAUTHORIZED" in tool_classes
    and "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT" in p1_checks
):
    derived_supported.add("dimension:authorization_and_scope_boundaries")

if (
    "AMBIGUOUS" in browser_classes
    and "AMBIGUITY_IS_PRESERVED_RATHER_THAN_GUESSED" in m0_checks
):
    derived_supported.add("dimension:routine_ambiguity")

if (
    "NO_SUFFICIENT_ROUTE" in tool_classes
    and "CORRECT_NO_ROUTE_ESCALATION" in tool_dims
    and "AMBIGUITY_IS_PRESERVED_RATHER_THAN_GUESSED" in m0_checks
):
    derived_supported.add("dimension:explicit_abstention_and_fail_closed_cases")

expected_supported = set(audit["direct_legacy_substrate_witnesses"])
assert derived_supported == expected_supported, (sorted(derived_supported), sorted(expected_supported))

derived_missing = all_atoms - derived_supported
assert derived_missing == set(audit["missing_from_unchanged_legacy_t2"])
assert len(derived_supported) == 6
assert len(derived_missing) == 10

# Independently verify the reason all five composition dimensions stay missing:
# the concrete T2 parent runner generates behavior-specific component results
# independently and then computes parent success as an AND. It never supplies one
# shared mutable composition case to multiple component generators.
assert "component_results = {" in runner_text
assert "parent_pass = bool(component_results) and all(" in runner_text
assert runner_binding["parent_portfolio_rule"].startswith(
    "FOR_EACH_PORTFOLIO__RUN_EACH_BOUND_MULTIPLEX_BEHAVIOR_ON_ITS_FROZEN_ROUTE_SPECIFIC_SCHEDULE__COMPUTE_PARENT_TERMINAL_ACCEPTANCE_AS_AND_OF_ALL_LOAD_BEARING_MULTIPLEX_COMPONENTS"
)
composition_atoms = {
    "dimension:research_plus_tool_use_plus_artifact_creation",
    "dimension:browser_or_computer_action_plus_memory_plus_recovery",
    "dimension:coding_plus_debugging_plus_tool_discovery",
    "dimension:delegation_plus_evidence_synthesis_plus_artifact_production",
    "dimension:cross_capability_state_handoff_and_rollback",
}
assert composition_atoms.issubset(derived_missing)

# The old source contracts do not directly bind the other five missing dimensions.
# This is a fail-closed direct-witness audit, not a claim that the underlying Brain
# is incapable of them.
other_missing = derived_missing - composition_atoms
assert other_missing == {
    "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types",
    "dimension:long_horizon_state_retention",
    "dimension:minimal_oversight_completion",
    "dimension:multi_constraint_instruction_compliance",
    "dimension:requirement_change",
}

assert audit["reuse_result"]["legacy_t2_unchanged_is_scope_superset"] is False
assert audit["reuse_result"]["consumed_terminal_v3_results_reused_for_new_acceptance"] is False
assert audit["fresh_reality_authority"] is False
assert audit["acceptance_credit_delta"] == 0

print(json.dumps({
    "status": "PASS",
    "all_dimension_count": len(all_atoms),
    "derived_supported_count": len(derived_supported),
    "derived_missing_count": len(derived_missing),
    "derived_supported": sorted(derived_supported),
    "derived_missing": sorted(derived_missing),
    "composition_missing_count": len(composition_atoms),
    "parent_runner_component_and_semantics_verified": True,
    "authority_delta": 0
}, indent=2, sort_keys=True))
