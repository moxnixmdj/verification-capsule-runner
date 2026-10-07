from __future__ import annotations

from canonical.runtime.matched_success_integrated_extension_v1 import (
    INTEGRATED_CLASS,
    LEGACY_ROUTE,
    REPETITIONS,
    TARGET_BY_ATOM,
    generate_cases,
    scope_input,
)
from canonical.runtime.matched_success_scope_compiler_v1 import compile_scope

EXPECTED_INTEGRATED = {
    "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types": {"browser", "tool", "delegation_v2"},
    "dimension:long_horizon_state_retention": {"browser", "tool", "delegation_v2"},
    "dimension:minimal_oversight_completion": {"browser", "tool", "delegation_v2"},
    "dimension:multi_constraint_instruction_compliance": {"m0", "m0_change", "delegation_v2"},
    "dimension:requirement_change": {"m0", "m0_change", "delegation_v2"},
    "dimension:research_plus_tool_use_plus_artifact_creation": {"tool", "p3", "native"},
    "dimension:browser_or_computer_action_plus_memory_plus_recovery": {"browser", "p1"},
    "dimension:coding_plus_debugging_plus_tool_discovery": {"structured", "p1", "tool"},
    "dimension:delegation_plus_evidence_synthesis_plus_artifact_production": {"delegation_v3", "p3", "native"},
    "dimension:cross_capability_state_handoff_and_rollback": {"delegation_v2", "tool", "p1", "p2"},
}
EXPECTED_LEGACY = {
    "dimension:state_change_after_actions_requiring_replanning",
    "dimension:tool_failure_and_recovery",
    "dimension:subtask_dependency_and_fan_in",
    "dimension:authorization_and_scope_boundaries",
    "dimension:routine_ambiguity",
    "dimension:explicit_abstention_and_fail_closed_cases",
}

assert set(INTEGRATED_CLASS) == set(EXPECTED_INTEGRATED)
assert set(LEGACY_ROUTE) == EXPECTED_LEGACY
assert set(TARGET_BY_ATOM) == set(EXPECTED_INTEGRATED) | EXPECTED_LEGACY
assert len(TARGET_BY_ATOM) == 16
assert REPETITIONS == 4

rows = generate_cases("INDEPENDENT_REHEARSAL_COMMITMENT", "INDEPENDENT_REHEARSAL_BEACON")
assert len(rows) == 64
assert len({r["case_id"] for r in rows}) == 64
assert len({r["case_payload_sha256"] for r in rows}) == 64
assert len({r["case_initial_state"]["mutable_namespace"] for r in rows}) == 64

counts = {}
for row in rows:
    atom = row["primary_atom"]
    counts[atom] = counts.get(atom, 0) + 1
    assert row["case_initial_state"]["cross_case_memory"] is None
    assert row["case_initial_state"]["result_history"] == []
    mode = row["case_payload"]["mode"]
    if atom in EXPECTED_INTEGRATED:
        assert mode == "INTEGRATED_EXTENSION"
        body = row["case_payload"]["payload"]
        kinds = {str(x["kind"]) for x in body["components"]}
        assert kinds == EXPECTED_INTEGRATED[atom], (atom, kinds)
        assert body["class_id"] == INTEGRATED_CLASS[atom]
        assert len(body["handoff_chain"]) == len(body["components"]) - 1
        if atom in {
            "dimension:multi_constraint_instruction_compliance",
            "dimension:requirement_change",
        }:
            m0_rows = [
                x for x in body["components"]
                if x["kind"] in {"m0", "m0_change"}
            ]
            assert len(m0_rows) == 2
            assert all(
                len(x["case"]["_oracle"]["requirements"]) >= 2
                for x in m0_rows
            )
            assert (
                m0_rows[0]["case"]["raw_source"]
                != m0_rows[1]["case"]["raw_source"]
            )
    else:
        assert mode == "LEGACY_SUBSTRATE_REUSE"

assert set(counts) == set(TARGET_BY_ATOM)
assert set(counts.values()) == {4}

rows2 = generate_cases("INDEPENDENT_REHEARSAL_COMMITMENT", "DIFFERENT_BEACON")
assert [r["case_id"] for r in rows2] == [r["case_id"] for r in rows]
assert [r["case_payload_sha256"] for r in rows2] != [r["case_payload_sha256"] for r in rows]

# The generator is forbidden to make its own coverage evidence authoritative.
unverified = scope_input(
    "INDEPENDENT_REHEARSAL_COMMITMENT",
    "INDEPENDENT_REHEARSAL_BEACON",
    generator_git_blob_sha="a" * 40,
    scorer_git_blob_sha="b" * 40,
    brain_commit_sha="c" * 40,
    tool_authority_sha256="d" * 64,
    target_interface_sha256="e" * 64,
)
out = compile_scope(unverified)
assert out["status"] == "FAIL_CLOSED"
assert "COVERAGE_NOT_VERIFIED" in out["errors"][0]

print("INDEPENDENT_SEMANTIC_VERIFIER_PASS")
